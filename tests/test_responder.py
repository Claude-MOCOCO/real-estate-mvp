"""응답 포맷터 테스트"""

from app.schemas.property import ParseResult
from app.services.responder import format_registered_summary, format_price


def test_format_price_eok():
    assert format_price(300000000) == "3억"


def test_format_price_eok_and_man():
    assert format_price(350000000) == "3억 5,000만원"


def test_format_price_man():
    assert format_price(50000000) == "5,000만원"


def test_format_price_none():
    assert format_price(None) == "-"


def test_format_registered_summary():
    parsed = ParseResult(
        intent="register",
        transaction_type="전세",
        price_main=300000000,
        area_pyeong=30,
        address_gugun="강남구",
        address_dong="역삼동",
        confidence=0.85,
    )
    result = format_registered_summary(parsed)
    assert "전세" in result
    assert "3억" in result
    assert "30" in result
    assert "강남구" in result


def test_format_registered_summary_with_monthly():
    parsed = ParseResult(
        intent="register",
        transaction_type="월세",
        price_main=10000000,
        price_monthly=500000,
        address_gugun="서초구",
        confidence=0.8,
    )
    result = format_registered_summary(parsed)
    assert "월세" in result
    assert "1,000만원" in result
    assert "50만원" in result
