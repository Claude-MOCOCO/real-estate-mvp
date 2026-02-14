"""FastMCP 서버 — 부동산 매물 관리 Tools + Resources"""

import os
import json
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from db import init_pool, close_pool, get_conn
from models import SearchParams, PropertyCreate, PropertyUpdate


@asynccontextmanager
async def lifespan(server):
    """MCP 서버 시작 시 DB 풀 초기화, 종료 시 정리"""
    await init_pool(os.environ["DATABASE_URL"])
    try:
        yield
    finally:
        await close_pool()


mcp = FastMCP("부동산 매물 관리", lifespan=lifespan)


# =============================================================================
# Tools (7개)
# =============================================================================

@mcp.tool()
async def search_properties(
    region: str = "",
    property_type: str | None = None,
    trade_type: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    status: str = "active",
    sort_by: str = "newest",
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """조건별 매물 검색. region은 시도/시군구/동 중 일부 입력."""
    params = SearchParams(
        region=region, property_type=property_type, trade_type=trade_type,
        min_price=min_price, max_price=max_price,
        min_area=min_area, max_area=max_area,
        status=status, sort_by=sort_by, page=page, page_size=page_size,
    )
    async with get_conn() as conn:
        where_clauses = ["deleted_at IS NULL"]
        args = []
        idx = 1

        if params.region:
            where_clauses.append(
                f"(sido || sigungu || dong) LIKE '%' || ${idx} || '%'"
            )
            args.append(params.region)
            idx += 1

        if params.property_type:
            where_clauses.append(f"property_type = ${idx}")
            args.append(params.property_type)
            idx += 1

        if params.trade_type:
            where_clauses.append(f"trade_type = ${idx}")
            args.append(params.trade_type)
            idx += 1

        if params.status:
            where_clauses.append(f"status = ${idx}")
            args.append(params.status)
            idx += 1

        # 가격 필터 (trade_type에 따라 대상 컬럼 분기)
        price_col = "COALESCE(sale_price, deposit)"
        if params.trade_type == "매매":
            price_col = "sale_price"
        elif params.trade_type in ("전세", "월세"):
            price_col = "deposit"

        if params.min_price is not None:
            where_clauses.append(f"{price_col} >= ${idx}")
            args.append(params.min_price)
            idx += 1

        if params.max_price is not None:
            where_clauses.append(f"{price_col} <= ${idx}")
            args.append(params.max_price)
            idx += 1

        if params.min_area is not None:
            where_clauses.append(f"area_exclusive_m2 >= ${idx}")
            args.append(params.min_area)
            idx += 1

        if params.max_area is not None:
            where_clauses.append(f"area_exclusive_m2 <= ${idx}")
            args.append(params.max_area)
            idx += 1

        where_sql = " AND ".join(where_clauses)

        # 정렬
        sort_map = {
            "newest": "created_at DESC",
            "price_asc": f"{price_col} ASC NULLS LAST",
            "price_desc": f"{price_col} DESC NULLS LAST",
            "area_asc": "area_exclusive_m2 ASC NULLS LAST",
            "area_desc": "area_exclusive_m2 DESC NULLS LAST",
        }
        order_sql = sort_map.get(params.sort_by, "created_at DESC")

        # COUNT
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM properties WHERE {where_sql}", *args
        )

        # SELECT
        offset = (params.page - 1) * params.page_size
        rows = await conn.fetch(
            f"""SELECT id, property_no, property_type, trade_type,
                       sido || ' ' || sigungu || ' ' || dong AS address_summary,
                       area_exclusive_m2, sale_price, deposit, monthly_rent,
                       status, created_at
                FROM properties WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT ${idx} OFFSET ${idx + 1}""",
            *args, params.page_size, offset,
        )

        return {
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
            "properties": [dict(r) for r in rows],
        }


@mcp.tool()
async def get_property_detail(
    property_id: int | None = None,
    property_no: str | None = None,
) -> dict:
    """매물 상세 조회 (변경이력 포함). property_id 또는 property_no 중 하나 필수."""
    if not property_id and not property_no:
        raise ValueError("property_id 또는 property_no 중 하나를 입력해주세요.")
    async with get_conn() as conn:
        if property_id:
            row = await conn.fetchrow(
                "SELECT * FROM properties WHERE id = $1 AND deleted_at IS NULL",
                property_id,
            )
        else:
            row = await conn.fetchrow(
                "SELECT * FROM properties WHERE property_no = $1 AND deleted_at IS NULL",
                property_no,
            )
        if not row:
            identifier = f"ID: {property_id}" if property_id else f"번호: {property_no}"
            raise ValueError(f"매물을 찾을 수 없습니다 ({identifier})")

        pid = row["id"]
        history = await conn.fetch(
            """SELECT field_name, old_value, new_value, changed_at
               FROM property_history WHERE property_id = $1
               ORDER BY changed_at DESC LIMIT 10""",
            pid,
        )

        result = dict(row)
        result["history"] = [dict(h) for h in history]
        return result


@mcp.tool()
async def create_property(
    property_type: str,
    trade_type: str,
    sido: str,
    sigungu: str,
    dong: str,
    area_exclusive_m2: float,
    sale_price: int | None = None,
    deposit: int | None = None,
    monthly_rent: int | None = None,
    address_detail: str | None = None,
    road_address: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    area_supply_m2: float | None = None,
    floor: str | None = None,
    total_floors: int | None = None,
    room_count: int | None = None,
    bathroom_count: int | None = None,
    direction: str | None = None,
    built_year: int | None = None,
    parking_available: bool | None = None,
    maintenance_fee: int | None = None,
    options: list[str] | None = None,
    tags: list[str] | None = None,
    memo: str | None = None,
    description: str | None = None,
    source: str | None = None,
    source_url: str | None = None,
) -> dict:
    """매물 등록. property_no는 자동 생성됩니다."""
    # Pydantic 검증
    data = PropertyCreate(
        property_type=property_type, trade_type=trade_type,
        sido=sido, sigungu=sigungu, dong=dong,
        area_exclusive_m2=area_exclusive_m2,
        sale_price=sale_price, deposit=deposit, monthly_rent=monthly_rent,
        address_detail=address_detail, road_address=road_address,
        latitude=latitude, longitude=longitude,
        area_supply_m2=area_supply_m2, floor=floor, total_floors=total_floors,
        room_count=room_count, bathroom_count=bathroom_count,
        direction=direction, built_year=built_year,
        parking_available=parking_available, maintenance_fee=maintenance_fee,
        options=options, tags=tags, memo=memo, description=description,
        source=source, source_url=source_url,
    )

    # None이 아닌 필드만 추출
    fields = {}
    for k, v in data.model_dump().items():
        if v is not None:
            fields[k] = v

    # options, tags는 JSONB로 변환
    if "options" in fields:
        fields["options"] = json.dumps(fields["options"], ensure_ascii=False)
    if "tags" in fields:
        fields["tags"] = json.dumps(fields["tags"], ensure_ascii=False)

    col_names = ", ".join(fields.keys())
    placeholders = ", ".join(f"${i+1}" for i in range(len(fields)))

    async with get_conn() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO properties ({col_names}) VALUES ({placeholders}) RETURNING *",
            *fields.values(),
        )
        return dict(row)


@mcp.tool()
async def update_property(
    property_id: int,
    property_type: str | None = None,
    trade_type: str | None = None,
    sido: str | None = None,
    sigungu: str | None = None,
    dong: str | None = None,
    address_detail: str | None = None,
    road_address: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    area_exclusive_m2: float | None = None,
    area_supply_m2: float | None = None,
    sale_price: int | None = None,
    deposit: int | None = None,
    monthly_rent: int | None = None,
    floor: str | None = None,
    total_floors: int | None = None,
    room_count: int | None = None,
    bathroom_count: int | None = None,
    direction: str | None = None,
    built_year: int | None = None,
    parking_available: bool | None = None,
    maintenance_fee: int | None = None,
    options: list[str] | None = None,
    tags: list[str] | None = None,
    memo: str | None = None,
    description: str | None = None,
    status: str | None = None,
    source: str | None = None,
    source_url: str | None = None,
) -> dict:
    """매물 수정. 변경된 필드만 전달합니다. 변경이력은 트리거가 자동 기록."""
    updates = {}
    local_vars = locals()
    for k in PropertyUpdate.model_fields:
        v = local_vars.get(k)
        if v is not None:
            updates[k] = v

    if not updates:
        raise ValueError("수정할 필드가 없습니다.")

    # options, tags는 JSONB로 변환
    if "options" in updates:
        updates["options"] = json.dumps(updates["options"], ensure_ascii=False)
    if "tags" in updates:
        updates["tags"] = json.dumps(updates["tags"], ensure_ascii=False)

    set_clauses = []
    args = []
    idx = 1
    for k, v in updates.items():
        set_clauses.append(f"{k} = ${idx}")
        args.append(v)
        idx += 1

    set_sql = ", ".join(set_clauses)
    args.append(property_id)

    async with get_conn() as conn:
        row = await conn.fetchrow(
            f"UPDATE properties SET {set_sql} "
            f"WHERE id = ${idx} AND deleted_at IS NULL "
            f"RETURNING *",
            *args,
        )
        if not row:
            raise ValueError(f"매물을 찾을 수 없거나 이미 삭제됨 (ID: {property_id})")
        return dict(row)


@mcp.tool()
async def delete_property(property_id: int) -> dict:
    """매물 삭제 (soft delete)"""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            "UPDATE properties SET deleted_at = NOW() "
            "WHERE id = $1 AND deleted_at IS NULL "
            "RETURNING id, property_no, deleted_at",
            property_id,
        )
        if not row:
            raise ValueError(f"매물을 찾을 수 없거나 이미 삭제됨 (ID: {property_id})")
        return {"success": True, **dict(row)}


@mcp.tool()
async def get_property_statistics(
    region: str | None = None,
    property_type: str | None = None,
    period: str = "this_month",
) -> dict:
    """매물 현황 통계"""
    async with get_conn() as conn:
        where_clauses = ["deleted_at IS NULL"]
        args = []
        idx = 1

        if region:
            where_clauses.append(
                f"(sido || sigungu) LIKE '%' || ${idx} || '%'"
            )
            args.append(region)
            idx += 1

        if property_type:
            where_clauses.append(f"property_type = ${idx}")
            args.append(property_type)
            idx += 1

        # 기간 필터
        if period == "this_month":
            where_clauses.append(
                "created_at >= date_trunc('month', CURRENT_DATE)"
            )
        elif period == "last_month":
            where_clauses.append(
                "created_at >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') "
                "AND created_at < date_trunc('month', CURRENT_DATE)"
            )
        elif period == "this_year":
            where_clauses.append(
                "created_at >= date_trunc('year', CURRENT_DATE)"
            )

        where_sql = " AND ".join(where_clauses)

        # 전체 건수
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM properties WHERE {where_sql}", *args
        )

        # 상태별
        status_rows = await conn.fetch(
            f"SELECT status, COUNT(*) as cnt FROM properties "
            f"WHERE {where_sql} GROUP BY status",
            *args,
        )
        by_status = {r["status"]: r["cnt"] for r in status_rows}

        # 유형별 (평균 가격 포함)
        type_rows = await conn.fetch(
            f"SELECT property_type, COUNT(*) as cnt, "
            f"AVG(COALESCE(sale_price, deposit)) as avg_price "
            f"FROM properties WHERE {where_sql} "
            f"GROUP BY property_type ORDER BY cnt DESC",
            *args,
        )
        by_type = [
            {"type": r["property_type"], "count": r["cnt"],
             "avg_price": int(r["avg_price"]) if r["avg_price"] else None}
            for r in type_rows
        ]

        # 지역별
        region_rows = await conn.fetch(
            f"SELECT sigungu, COUNT(*) as cnt, "
            f"AVG(COALESCE(sale_price, deposit)) as avg_price "
            f"FROM properties WHERE {where_sql} "
            f"GROUP BY sigungu ORDER BY cnt DESC",
            *args,
        )
        by_region = [
            {"region": r["sigungu"], "count": r["cnt"],
             "avg_price": int(r["avg_price"]) if r["avg_price"] else None}
            for r in region_rows
        ]

        return {
            "total_count": total,
            "by_status": by_status,
            "by_type": by_type,
            "by_region": by_region,
            "period": period,
        }


@mcp.tool()
async def compare_properties(property_ids: list[int]) -> dict:
    """2~5개 매물 비교"""
    if len(property_ids) < 2 or len(property_ids) > 5:
        raise ValueError("비교는 2~5개 매물만 가능합니다.")

    async with get_conn() as conn:
        placeholders = ", ".join(f"${i+1}" for i in range(len(property_ids)))
        rows = await conn.fetch(
            f"SELECT * FROM properties WHERE id IN ({placeholders}) AND deleted_at IS NULL",
            *property_ids,
        )

        if len(rows) < 2:
            raise ValueError("비교 가능한 매물이 2개 미만입니다. 매물 ID를 확인해주세요.")

        properties = [dict(r) for r in rows]

        # 비교 요약
        prices = [p.get("sale_price") or p.get("deposit") for p in properties if p.get("sale_price") or p.get("deposit")]
        areas = [float(p["area_exclusive_m2"]) for p in properties if p.get("area_exclusive_m2")]

        summary = {
            "count": len(properties),
            "price_range": {"min": min(prices), "max": max(prices)} if prices else None,
            "area_range": {"min": min(areas), "max": max(areas)} if areas else None,
        }

        return {
            "properties": properties,
            "comparison_summary": summary,
        }


# =============================================================================
# Resources (3개)
# =============================================================================

@mcp.resource("property://list")
async def list_properties() -> str:
    """전체 활성 매물 요약"""
    async with get_conn() as conn:
        rows = await conn.fetch(
            "SELECT id, property_no, property_type, trade_type, "
            "sido || ' ' || sigungu || ' ' || dong AS region, "
            "sale_price, deposit, monthly_rent "
            "FROM properties WHERE deleted_at IS NULL AND status = 'active' "
            "ORDER BY created_at DESC"
        )
        return json.dumps([dict(r) for r in rows], default=str, ensure_ascii=False)


@mcp.resource("property://list/{region}")
async def list_properties_by_region(region: str) -> str:
    """지역별 활성 매물"""
    async with get_conn() as conn:
        rows = await conn.fetch(
            "SELECT id, property_no, property_type, trade_type, "
            "sido || ' ' || sigungu || ' ' || dong AS region, "
            "sale_price, deposit, monthly_rent "
            "FROM properties WHERE deleted_at IS NULL AND status = 'active' "
            "AND (sido LIKE '%' || $1 || '%' OR sigungu LIKE '%' || $1 || '%') "
            "ORDER BY created_at DESC",
            region,
        )
        return json.dumps([dict(r) for r in rows], default=str, ensure_ascii=False)


@mcp.resource("property://{id}")
async def get_property_resource(id: int) -> str:
    """개별 매물 상세"""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM properties WHERE id = $1 AND deleted_at IS NULL", id
        )
        if not row:
            return json.dumps({"error": f"매물을 찾을 수 없습니다 (ID: {id})"}, ensure_ascii=False)
        return json.dumps(dict(row), default=str, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
