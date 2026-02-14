"""응답 포맷터 확장 테스트 — format_property_summary, format_search_results, format_delete_confirm"""

from unittest.mock import MagicMock

from app.services.responder import (
    format_delete_confirm,
    format_price,
    format_property_summary,
    format_search_results,
)


def _mock_property(**kwargs):
    prop = MagicMock()
    prop.transaction_type = kwargs.get("transaction_type", None)
    prop.address_gugun = kwargs.get("address_gugun", None)
    prop.address_dong = kwargs.get("address_dong", None)
    prop.building_name = kwargs.get("building_name", None)
    prop.area_pyeong = kwargs.get("area_pyeong", None)
    prop.price_main = kwargs.get("price_main", None)
    prop.price_monthly = kwargs.get("price_monthly", None)
    return prop


def test_format_price_zero():
    assert format_price(0) == "-"


def test_format_price_small_won():
    assert format_price(5000) == "5,000원"


def test_format_property_summary_full():
    prop = _mock_property(
        transaction_type="전세",
        address_gugun="강남구",
        address_dong="역삼동",
        building_name="래미안",
        area_pyeong=30.0,
        price_main=300000000,
    )
    result = format_property_summary(prop)
    assert "[전세]" in result
    assert "강남구" in result
    assert "역삼동" in result
    assert "래미안" in result
    assert "30" in result
    assert "3억" in result


def test_format_property_summary_monthly():
    prop = _mock_property(
        transaction_type="월세",
        address_gugun="서초구",
        price_main=10000000,
        price_monthly=500000,
    )
    result = format_property_summary(prop)
    assert "[월세]" in result
    assert "1,000만원" in result
    assert "월 50만원" in result


def test_format_property_summary_minimal():
    prop = _mock_property()
    result = format_property_summary(prop)
    assert result == ""


def test_format_search_results_empty():
    assert format_search_results([]) == "조건에 맞는 매물이 없어요."


def test_format_search_results_multiple():
    props = [
        _mock_property(transaction_type="전세", address_gugun="강남구", price_main=300000000),
        _mock_property(transaction_type="월세", address_gugun="서초구", price_main=10000000),
    ]
    result = format_search_results(props)
    assert "총 2건" in result
    assert "1." in result
    assert "2." in result
    assert "강남구" in result
    assert "서초구" in result


def test_format_delete_confirm():
    prop = _mock_property(transaction_type="전세", address_gugun="강남구", price_main=300000000)
    result = format_delete_confirm(prop)
    assert "삭제할까요" in result
    assert "강남구" in result
