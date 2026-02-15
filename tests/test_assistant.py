"""개인비서 핵심 유스케이스 테스트 — Mock Repository/Parser 기반

헥사고날 아키텍처: UseCase에 Mock 포트를 주입하여 순수 비즈니스 로직만 테스트.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.use_cases import (
    CONFIDENCE_THRESHOLD,
    MAX_DELETE_OPTIONS,
    MAX_MEMO_DISPLAY,
    AssistantUseCase,
    _summarize_parsed,
)
from app.domain.value_objects import ParseResult


def _make_use_case(
    agent_repo=None,
    property_repo=None,
    memo_repo=None,
    parser=None,
):
    """Mock 포트를 주입하여 UseCase 인스턴스 생성"""
    return AssistantUseCase(
        agent_repo=agent_repo or AsyncMock(),
        property_repo=property_repo or AsyncMock(),
        memo_repo=memo_repo or AsyncMock(),
        parser=parser or AsyncMock(),
    )


def test_handle_update():
    uc = _make_use_case()
    parsed = ParseResult(intent="update", confidence=0.9)
    result = uc._handle_update(parsed)
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

    agent_repo = AsyncMock()
    agent_repo.get_or_create.return_value = mock_agent

    property_repo = AsyncMock()
    property_repo.create_from_parse.return_value = MagicMock()

    parser = AsyncMock()
    parser.parse.return_value = parsed

    uc = _make_use_case(
        agent_repo=agent_repo,
        property_repo=property_repo,
        parser=parser,
    )

    result = await uc.handle_utterance("test_user", "강남구 역삼동 30평 전세 3억 등록")

    assert "등록됐어요" in result
    property_repo.create_from_parse.assert_called_once()


@pytest.mark.asyncio
async def test_handle_utterance_register_low_confidence():
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(intent="register", confidence=0.1)

    agent_repo = AsyncMock()
    agent_repo.get_or_create.return_value = mock_agent

    parser = AsyncMock()
    parser.parse.return_value = parsed

    uc = _make_use_case(agent_repo=agent_repo, parser=parser)

    result = await uc.handle_utterance("test_user", "뭔가 이상한 입력")

    assert "충분히 파악하지 못했어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_register_no_transaction_type():
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(
        intent="register",
        address_gugun="강남구",
        price_main=300000000,
        confidence=0.9,
    )

    agent_repo = AsyncMock()
    agent_repo.get_or_create.return_value = mock_agent

    parser = AsyncMock()
    parser.parse.return_value = parsed

    uc = _make_use_case(agent_repo=agent_repo, parser=parser)

    result = await uc.handle_utterance("test_user", "강남구 30평 3억 등록")

    assert "거래 유형" in result


@pytest.mark.asyncio
async def test_handle_utterance_search_empty():
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(
        intent="search",
        address_gugun="강남구",
        confidence=0.9,
    )

    agent_repo = AsyncMock()
    agent_repo.get_or_create.return_value = mock_agent

    property_repo = AsyncMock()
    property_repo.search.return_value = []

    parser = AsyncMock()
    parser.parse.return_value = parsed

    uc = _make_use_case(
        agent_repo=agent_repo,
        property_repo=property_repo,
        parser=parser,
    )

    result = await uc.handle_utterance("test_user", "강남구 매물 있어?")

    assert "없어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_delete_not_found():
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(intent="delete", address_gugun="강남구", confidence=0.9)

    agent_repo = AsyncMock()
    agent_repo.get_or_create.return_value = mock_agent

    property_repo = AsyncMock()
    property_repo.search.return_value = []

    parser = AsyncMock()
    parser.parse.return_value = parsed

    uc = _make_use_case(
        agent_repo=agent_repo,
        property_repo=property_repo,
        parser=parser,
    )

    result = await uc.handle_utterance("test_user", "강남구 매물 삭제")

    assert "찾지 못했어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_delete_single():
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

    agent_repo = AsyncMock()
    agent_repo.get_or_create.return_value = mock_agent

    property_repo = AsyncMock()
    property_repo.search.return_value = [mock_prop]
    property_repo.delete.return_value = True

    parser = AsyncMock()
    parser.parse.return_value = parsed

    uc = _make_use_case(
        agent_repo=agent_repo,
        property_repo=property_repo,
        parser=parser,
    )

    result = await uc.handle_utterance("test_user", "강남구 전세 3억 삭제")

    assert "삭제됐어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_unknown_saves_memo():
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    mock_memo = MagicMock()
    parsed = ParseResult(intent="unknown", confidence=0.1)

    agent_repo = AsyncMock()
    agent_repo.get_or_create.return_value = mock_agent

    memo_repo = AsyncMock()
    memo_repo.create.return_value = (mock_memo, True)

    parser = AsyncMock()
    parser.parse.return_value = parsed

    uc = _make_use_case(
        agent_repo=agent_repo,
        memo_repo=memo_repo,
        parser=parser,
    )

    result = await uc.handle_utterance("test_user", "오늘 날씨 좋다")

    assert "메모로 저장" in result


@pytest.mark.asyncio
async def test_handle_utterance_unknown_duplicate_memo():
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    mock_memo = MagicMock()
    parsed = ParseResult(intent="unknown", confidence=0.1)

    agent_repo = AsyncMock()
    agent_repo.get_or_create.return_value = mock_agent

    memo_repo = AsyncMock()
    memo_repo.create.return_value = (mock_memo, False)

    parser = AsyncMock()
    parser.parse.return_value = parsed

    uc = _make_use_case(
        agent_repo=agent_repo,
        memo_repo=memo_repo,
        parser=parser,
    )

    result = await uc.handle_utterance("test_user", "오늘 날씨 좋다")

    assert "이미 메모에 저장돼 있어요" in result


@pytest.mark.asyncio
async def test_handle_utterance_list_memo_empty():
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"

    parsed = ParseResult(intent="list_memo", confidence=0.9)

    agent_repo = AsyncMock()
    agent_repo.get_or_create.return_value = mock_agent

    memo_repo = AsyncMock()
    memo_repo.list_by_agent.return_value = []

    parser = AsyncMock()
    parser.parse.return_value = parsed

    uc = _make_use_case(
        agent_repo=agent_repo,
        memo_repo=memo_repo,
        parser=parser,
    )

    result = await uc.handle_utterance("test_user", "메모 보여줘")

    assert "없어요" in result
