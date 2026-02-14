"""AI 파싱 모듈 테스트 — Mock을 사용하여 OpenAI 호출 없이 테스트"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.parser import PropertyParser


@pytest.fixture
def parser():
    p = PropertyParser()
    p._client = MagicMock()
    return p


def _mock_completion(data: dict):
    """OpenAI 응답 Mock 생성"""
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(data)
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.mark.asyncio
async def test_parse_register_apartment(parser):
    mock_data = {
        "intent": "register",
        "transaction_type": "전세",
        "price_main": 300000000,
        "price_monthly": None,
        "area_pyeong": 30,
        "address_sido": "서울",
        "address_gugun": "강남구",
        "address_dong": "역삼동",
        "building_name": None,
        "extra": {},
        "missing_fields": ["building_name"],
        "confidence": 0.85,
        "clarification_needed": "건물명을 알려주시면 더 정확히 등록할 수 있어요.",
    }

    parser._client.chat.completions.create = AsyncMock(
        return_value=_mock_completion(mock_data)
    )
    result = await parser.parse("강남구 역삼동 30평대 전세 3억 아파트 등록해줘")

    assert result.intent == "register"
    assert result.transaction_type == "전세"
    assert result.price_main == 300000000
    assert result.area_pyeong == 30
    assert result.address_gugun == "강남구"
    assert result.confidence == 0.85


@pytest.mark.asyncio
async def test_parse_search(parser):
    mock_data = {
        "intent": "search",
        "transaction_type": "월세",
        "price_main": None,
        "price_monthly": None,
        "area_pyeong": None,
        "address_sido": None,
        "address_gugun": None,
        "address_dong": "역삼동",
        "building_name": None,
        "extra": {},
        "missing_fields": [],
        "confidence": 0.9,
        "clarification_needed": None,
    }

    parser._client.chat.completions.create = AsyncMock(
        return_value=_mock_completion(mock_data)
    )
    result = await parser.parse("역삼동 월세 뭐 있어?")

    assert result.intent == "search"
    assert result.transaction_type == "월세"
    assert result.address_dong == "역삼동"


@pytest.mark.asyncio
async def test_parse_json_error(parser):
    mock_choice = MagicMock()
    mock_choice.message.content = "이것은 JSON이 아닙니다"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    parser._client.chat.completions.create = AsyncMock(return_value=mock_response)
    result = await parser.parse("이상한 입력")

    assert result.intent == "unknown"
    assert result.confidence == 0.0
    assert result.clarification_needed is not None


@pytest.mark.asyncio
async def test_parse_api_error(parser):
    parser._client.chat.completions.create = AsyncMock(
        side_effect=Exception("API 오류")
    )
    result = await parser.parse("테스트")

    assert result.intent == "unknown"
    assert result.confidence == 0.0
