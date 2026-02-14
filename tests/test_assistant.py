"""개인비서 핵심 로직 테스트 — Mock DB/Parser 기반"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.property import ParseResult
from app.services.assistant import (
    CONFIDENCE_THRESHOLD,
    MAX_DELETE_OPTIONS,
    MAX_MEMO_DISPLAY,
    _handle_update,
    _summarize_parsed,
    handle_utterance,
)


def test_handle_update():
    parsed = ParseResult(intent="update", confidence=0.9)
    result = _handle_update(parsed)
    assert "준비 중" in result
    assert "삭제 후 다시 등록" in result


def test_summarize_parsed_full():
    parsed = ParseResult(
        intent="register",
        address_gugun="강남구",
        address_dong="역삼동",
        area_pyeong=30.0,
        price_main=300000000,
        building_name="래미안",
        confidence=0.9,
    )
    result = _summarize_parsed(parsed)
    assert "강남구" in result
    assert "역삼동" in result
    assert "30.0평" in result
    assert "3억" in result
    assert "래미안" in result


def test_summarize_parsed_empty():
    parsed = ParseResult(intent="register", confidence=0.5)
    result = _summarize_parsed(parsed)
    assert result == "(추출된 정보 없음)"


@pytest.mark.asyncio
async def test_handle_utterance_register():
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(
        intent="register",
        transaction_type="전세",
        price_main=300000000,
        area_pyeong=30.0,
        address_gugun="강남구",
        confidence=0.9,
    )

    with (
        patch("app.services.assistant.get_or_create_agent", new_callable=AsyncMock, return_value=mock_agent),
        patch("app.services.assistant.parser") as mock_parser,
        patch("app.services.assistant.create_property_from_parse", new_callable=AsyncMock) as mock_create,
    ):
        mock_parser.parse = AsyncMock(return_value=parsed)
        mock_create.return_value = MagicMock()

        result = await handle_utterance(mock_db, "test_user", "강남구 역삼동 30평 전세 3억 등록")

    assert "등록됐어요" in result
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_handle_utterance_register_low_confidence():
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(intent="register", confidence=0.1)

    with (
        patch("app.services.assistant.get_or_create_agent", new_callable=AsyncMock, return_value=mock_agent),
        patch("app.services.assistant.parser") as mock_parser,
    ):
        mock_parser.parse = AsyncMock(return_value=parsed)

        result = await handle_utterance(mock_db, "test_user", "뭔가 이상한 입력")

    assert "충분히 파악하지 못했어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_register_no_transaction_type():
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(
        intent="register",
        address_gugun="강남구",
        price_main=300000000,
        confidence=0.9,
    )

    with (
        patch("app.services.assistant.get_or_create_agent", new_callable=AsyncMock, return_value=mock_agent),
        patch("app.services.assistant.parser") as mock_parser,
    ):
        mock_parser.parse = AsyncMock(return_value=parsed)

        result = await handle_utterance(mock_db, "test_user", "강남구 30평 3억 등록")

    assert "거래 유형" in result


@pytest.mark.asyncio
async def test_handle_utterance_search_empty():
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(
        intent="search",
        address_gugun="강남구",
        confidence=0.9,
    )

    with (
        patch("app.services.assistant.get_or_create_agent", new_callable=AsyncMock, return_value=mock_agent),
        patch("app.services.assistant.parser") as mock_parser,
        patch("app.services.assistant.search_properties", new_callable=AsyncMock, return_value=[]),
    ):
        mock_parser.parse = AsyncMock(return_value=parsed)

        result = await handle_utterance(mock_db, "test_user", "강남구 매물 있어?")

    assert "없어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_delete_not_found():
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(intent="delete", address_gugun="강남구", confidence=0.9)

    with (
        patch("app.services.assistant.get_or_create_agent", new_callable=AsyncMock, return_value=mock_agent),
        patch("app.services.assistant.parser") as mock_parser,
        patch("app.services.assistant.search_properties", new_callable=AsyncMock, return_value=[]),
    ):
        mock_parser.parse = AsyncMock(return_value=parsed)

        result = await handle_utterance(mock_db, "test_user", "강남구 매물 삭제")

    assert "찾지 못했어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_delete_single():
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    mock_prop = MagicMock()
    mock_prop.id = "prop-1"
    mock_prop.transaction_type = "전세"
    mock_prop.address_gugun = "강남구"
    mock_prop.address_dong = None
    mock_prop.building_name = None
    mock_prop.area_pyeong = None
    mock_prop.price_main = 300000000
    mock_prop.price_monthly = None

    parsed = ParseResult(intent="delete", address_gugun="강남구", confidence=0.9)

    with (
        patch("app.services.assistant.get_or_create_agent", new_callable=AsyncMock, return_value=mock_agent),
        patch("app.services.assistant.parser") as mock_parser,
        patch("app.services.assistant.search_properties", new_callable=AsyncMock, return_value=[mock_prop]),
        patch("app.services.assistant.delete_property", new_callable=AsyncMock, return_value=True),
    ):
        mock_parser.parse = AsyncMock(return_value=parsed)

        result = await handle_utterance(mock_db, "test_user", "강남구 전세 3억 삭제")

    assert "삭제됐어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_unknown_saves_memo():
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    mock_memo = MagicMock()
    parsed = ParseResult(intent="unknown", confidence=0.1)

    with (
        patch("app.services.assistant.get_or_create_agent", new_callable=AsyncMock, return_value=mock_agent),
        patch("app.services.assistant.parser") as mock_parser,
        patch("app.services.assistant.create_memo", new_callable=AsyncMock, return_value=(mock_memo, True)),
    ):
        mock_parser.parse = AsyncMock(return_value=parsed)

        result = await handle_utterance(mock_db, "test_user", "오늘 날씨 좋다")

    assert "메모로 저장" in result


@pytest.mark.asyncio
async def test_handle_utterance_unknown_duplicate_memo():
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    mock_memo = MagicMock()
    parsed = ParseResult(intent="unknown", confidence=0.1)

    with (
        patch("app.services.assistant.get_or_create_agent", new_callable=AsyncMock, return_value=mock_agent),
        patch("app.services.assistant.parser") as mock_parser,
        patch("app.services.assistant.create_memo", new_callable=AsyncMock, return_value=(mock_memo, False)),
    ):
        mock_parser.parse = AsyncMock(return_value=parsed)

        result = await handle_utterance(mock_db, "test_user", "오늘 날씨 좋다")

    assert "이미 메모에 저장돼 있어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_list_memo_empty():
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(intent="list_memo", confidence=0.9)

    with (
        patch("app.services.assistant.get_or_create_agent", new_callable=AsyncMock, return_value=mock_agent),
        patch("app.services.assistant.parser") as mock_parser,
        patch("app.services.assistant.list_memos", new_callable=AsyncMock, return_value=[]),
    ):
        mock_parser.parse = AsyncMock(return_value=parsed)

        result = await handle_utterance(mock_db, "test_user", "메모 보여줘")

    assert "없어요" in result
