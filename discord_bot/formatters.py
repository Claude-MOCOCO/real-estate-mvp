"""Discord 메시지 포맷팅 유틸리티"""


def format_price(price_man: int | None) -> str:
    """만원 단위 가격을 억/만 표시로 변환"""
    if price_man is None:
        return "-"
    if price_man >= 10000:
        eok = price_man // 10000
        man = price_man % 10000
        if man == 0:
            return f"{eok}억"
        return f"{eok}억 {man:,}만"
    return f"{price_man:,}만"


def format_area(m2: float | None) -> str:
    """m2를 m2(평) 형식으로 변환"""
    if m2 is None:
        return "-"
    pyeong = m2 / 3.3058
    return f"{m2}m²({pyeong:.1f}평)"


def split_message(text: str, limit: int = 2000) -> list[str]:
    """2000자 초과 시 줄바꿈 기준으로 분할. 코드블록 내부는 깨지지 않도록 처리."""
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # 줄바꿈 기준 분할 (limit 이내 마지막 줄바꿈)
        split_idx = text.rfind('\n', 0, limit)
        if split_idx == -1:
            split_idx = limit
        chunks.append(text[:split_idx])
        text = text[split_idx:].lstrip('\n')
    return chunks


async def send_long_message(channel, text: str):
    """분할 전송 래퍼"""
    for chunk in split_message(text):
        await channel.send(chunk)
