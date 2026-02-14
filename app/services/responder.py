"""사용자 응답 메시지 포맷팅"""

from app.models.property import Property
from app.schemas.property import ParseResult


def format_price(amount: int | None) -> str:
    if amount is None or amount == 0:
        return "-"
    eok = amount // 100_000_000
    man = (amount % 100_000_000) // 10_000
    if eok and man:
        return f"{eok}억 {man:,}만원"
    elif eok:
        return f"{eok}억"
    elif man:
        return f"{man:,}만원"
    return f"{amount:,}원"


def format_property_summary(prop: Property) -> str:
    parts = []
    if prop.transaction_type:
        parts.append(f"[{prop.transaction_type}]")
    if prop.address_gugun:
        parts.append(prop.address_gugun)
    if prop.address_dong:
        parts.append(prop.address_dong)
    if prop.building_name:
        parts.append(prop.building_name)
    if prop.area_pyeong:
        parts.append(f"{prop.area_pyeong}평")
    if prop.price_main:
        parts.append(format_price(prop.price_main))
    if prop.price_monthly:
        parts.append(f"/ 월 {format_price(prop.price_monthly)}")
    return " ".join(parts)


def format_registered_summary(parsed: ParseResult) -> str:
    """등록 완료 요약 메시지 생성"""
    lines = []

    if parsed.transaction_type:
        lines.append(f"거래유형: {parsed.transaction_type}")
    if parsed.price_main:
        lines.append(f"가격: {format_price(parsed.price_main)}")
    if parsed.price_monthly:
        lines.append(f"월세: {format_price(parsed.price_monthly)}")
    if parsed.area_pyeong:
        lines.append(f"면적: {parsed.area_pyeong}평")

    address_parts = []
    if parsed.address_sido:
        address_parts.append(parsed.address_sido)
    if parsed.address_gugun:
        address_parts.append(parsed.address_gugun)
    if parsed.address_dong:
        address_parts.append(parsed.address_dong)
    if address_parts:
        lines.append(f"위치: {' '.join(address_parts)}")

    if parsed.building_name:
        lines.append(f"건물명: {parsed.building_name}")

    if parsed.extra:
        extras = []
        for k, v in parsed.extra.items():
            extras.append(f"{k}: {v}")
        if extras:
            lines.append(f"기타: {', '.join(extras)}")

    if parsed.missing_fields:
        lines.append(f"\n* 추가하면 좋을 정보: {', '.join(parsed.missing_fields)}")

    return "\n".join(lines)


def format_search_results(properties: list[Property]) -> str:
    if not properties:
        return "조건에 맞는 매물이 없어요."

    lines = [f"총 {len(properties)}건의 매물을 찾았어요.\n"]
    for i, prop in enumerate(properties, 1):
        lines.append(f"{i}. {format_property_summary(prop)}")

    return "\n".join(lines)


def format_delete_confirm(prop: Property) -> str:
    return f"아래 매물을 삭제할까요?\n\n{format_property_summary(prop)}\n\n'네' 또는 '삭제'라고 답해주시면 삭제됩니다."
