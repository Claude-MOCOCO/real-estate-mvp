import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.memo import Memo
from app.models.property import Property
from app.schemas.property import MemoCreate, ParseResult, PropertyCreate, PropertyStatus, PropertyUpdate

logger = logging.getLogger(__name__)

# 검색 상수
SEARCH_MAX_RESULTS = 20
PRICE_MARGIN_RATIO = 0.2
AREA_MARGIN_PYEONG = 5.0


async def get_or_create_agent(db: AsyncSession, kakao_user_id: str) -> Agent:
    """카카오 사용자 ID로 Agent 조회 또는 생성 (race condition 방어)"""
    result = await db.execute(
        select(Agent).where(Agent.kakao_user_id == kakao_user_id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        try:
            agent = Agent(kakao_user_id=kakao_user_id)
            db.add(agent)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(Agent).where(Agent.kakao_user_id == kakao_user_id)
            )
            agent = result.scalar_one_or_none()
            if agent is None:
                raise RuntimeError(f"Agent 생성/조회 실패: kakao_user_id={kakao_user_id}")
    return agent


async def create_property(
    db: AsyncSession, agent_id: uuid.UUID, data: PropertyCreate
) -> Property:
    try:
        prop = Property(agent_id=agent_id, **data.model_dump())
        db.add(prop)
        await db.commit()
        await db.refresh(prop)
        logger.info("매물 생성: id=%s, agent=%s", prop.id, agent_id)
        return prop
    except IntegrityError as e:
        await db.rollback()
        logger.error("매물 생성 실패 (제약조건): agent=%s, error=%s", agent_id, e)
        raise


async def create_property_from_parse(
    db: AsyncSession, agent_id: uuid.UUID, parsed: ParseResult, raw_input: str
) -> Property:
    """파싱 결과로 매물 생성"""
    try:
        prop = Property(
            agent_id=agent_id,
            transaction_type=parsed.transaction_type,
            price_main=parsed.price_main,
            price_monthly=parsed.price_monthly,
            area_pyeong=parsed.area_pyeong,
            address_sido=parsed.address_sido,
            address_gugun=parsed.address_gugun,
            address_dong=parsed.address_dong,
            building_name=parsed.building_name,
            extra=parsed.extra,
            raw_input=raw_input,
        )
        db.add(prop)
        await db.commit()
        await db.refresh(prop)
        logger.info("매물 등록(파싱): id=%s, agent=%s, type=%s", prop.id, agent_id, parsed.transaction_type)
        return prop
    except IntegrityError as e:
        await db.rollback()
        logger.error("매물 등록 실패 (제약조건): agent=%s, error=%s", agent_id, e)
        raise


async def list_properties(
    db: AsyncSession,
    agent_id: uuid.UUID,
    transaction_type: str | None = None,
    address_gugun: str | None = None,
    status: str = PropertyStatus.ACTIVE.value,
    limit: int = 50,
    offset: int = 0,
) -> list[Property]:
    """매물 목록 조회 (개인화 격리: agent_id 필수, 페이지네이션 적용)"""
    query = select(Property).where(
        Property.agent_id == agent_id,
        Property.status == status,
    )
    if transaction_type:
        query = query.where(Property.transaction_type == transaction_type)
    if address_gugun:
        query = query.where(Property.address_gugun == address_gugun)

    query = query.order_by(Property.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_property(
    db: AsyncSession, agent_id: uuid.UUID, property_id: uuid.UUID
) -> Property | None:
    """매물 단건 조회 (개인화 격리)"""
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.agent_id == agent_id,
        )
    )
    return result.scalar_one_or_none()


async def update_property(
    db: AsyncSession,
    agent_id: uuid.UUID,
    property_id: uuid.UUID,
    data: PropertyUpdate,
) -> Property | None:
    prop = await get_property(db, agent_id, property_id)
    if prop is None:
        return None

    UPDATABLE_FIELDS = {
        "transaction_type", "price_main", "price_monthly", "area_pyeong",
        "address_sido", "address_gugun", "address_dong", "building_name", "extra",
    }
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key not in UPDATABLE_FIELDS:
            continue
        setattr(prop, key, value)

    try:
        await db.commit()
        await db.refresh(prop)
        return prop
    except IntegrityError as e:
        await db.rollback()
        logger.error("매물 수정 실패 (제약조건): id=%s, agent=%s, error=%s", property_id, agent_id, e)
        raise


async def delete_property(
    db: AsyncSession, agent_id: uuid.UUID, property_id: uuid.UUID
) -> bool:
    """소프트 삭제"""
    prop = await get_property(db, agent_id, property_id)
    if prop is None:
        return False
    prop.status = PropertyStatus.DELETED.value
    await db.commit()
    logger.info("매물 삭제: id=%s, agent=%s", property_id, agent_id)
    return True


def _escape_like(value: str) -> str:
    r"""LIKE 쿼리 특수문자(%, _, \) 이스케이프"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def search_properties(
    db: AsyncSession, agent_id: uuid.UUID, parsed: ParseResult
) -> list[Property]:
    """파싱 결과 기반 매물 검색"""
    query = select(Property).where(
        Property.agent_id == agent_id,
        Property.status == PropertyStatus.ACTIVE.value,
    )

    if parsed.transaction_type:
        query = query.where(Property.transaction_type == parsed.transaction_type)
    if parsed.address_gugun:
        query = query.where(Property.address_gugun == parsed.address_gugun)
    if parsed.address_dong:
        query = query.where(Property.address_dong == parsed.address_dong)
    if parsed.building_name:
        escaped = _escape_like(parsed.building_name)
        query = query.where(Property.building_name.ilike(f"%{escaped}%", escape="\\"))
    if parsed.area_pyeong:
        min_area = max(0.1, parsed.area_pyeong - AREA_MARGIN_PYEONG)
        query = query.where(
            Property.area_pyeong.between(
                min_area,
                parsed.area_pyeong + AREA_MARGIN_PYEONG,
            )
        )
    if parsed.price_main:
        margin = int(parsed.price_main * PRICE_MARGIN_RATIO)
        min_price = max(0, parsed.price_main - margin)
        query = query.where(
            Property.price_main.between(min_price, parsed.price_main + margin)
        )

    query = query.order_by(Property.created_at.desc()).limit(SEARCH_MAX_RESULTS)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_memo(
    db: AsyncSession, agent_id: uuid.UUID, data: MemoCreate
) -> tuple[Memo, bool]:
    """메모 생성. 반환: (memo, is_new) — is_new=False면 중복 스킵됨"""
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await db.execute(
        select(Memo).where(
            Memo.agent_id == agent_id,
            Memo.content == data.content,
            Memo.created_at >= one_hour_ago,
        )
    )
    existing_memo = result.scalar_one_or_none()
    if existing_memo:
        logger.info("중복 메모 저장 스킵: agent=%s", agent_id)
        return existing_memo, False

    try:
        memo = Memo(agent_id=agent_id, content=data.content)
        db.add(memo)
        await db.commit()
        await db.refresh(memo)
        return memo, True
    except IntegrityError as e:
        await db.rollback()
        logger.error("메모 생성 실패 (제약조건): agent=%s, error=%s", agent_id, e)
        raise


async def list_memos(
    db: AsyncSession, agent_id: uuid.UUID, resolved: bool = False, limit: int = 50
) -> list[Memo]:
    result = await db.execute(
        select(Memo)
        .where(Memo.agent_id == agent_id, Memo.resolved == resolved)
        .order_by(Memo.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
