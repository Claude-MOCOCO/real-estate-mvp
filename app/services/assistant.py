"""개인비서 핵심 로직 — 자연어 입력을 해석하고 적절한 행동을 수행"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.property import MemoCreate, ParseResult
from app.services.parser import parser
from app.services.property_service import (
    create_memo,
    create_property_from_parse,
    delete_property,
    get_or_create_agent,
    list_memos,
    list_properties,
    search_properties,
)
from app.services.responder import (
    format_property_summary,
    format_registered_summary,
    format_search_results,
)

logger = logging.getLogger(__name__)


async def handle_utterance(db: AsyncSession, kakao_user_id: str, utterance: str) -> str:
    """사용자 발화를 처리하고 응답 텍스트를 반환"""

    agent = await get_or_create_agent(db, kakao_user_id)
    parsed = await parser.parse(utterance)

    logger.info(
        "파싱 결과: intent=%s, confidence=%.2f, user=%s",
        parsed.intent, parsed.confidence, kakao_user_id,
    )

    if parsed.intent == "register":
        return await _handle_register(db, agent.id, parsed, utterance)
    elif parsed.intent == "search":
        return await _handle_search(db, agent.id, parsed)
    elif parsed.intent == "update":
        return _handle_update(parsed)
    elif parsed.intent == "delete":
        return await _handle_delete(db, agent.id, parsed)
    elif parsed.intent == "list_memo":
        return await _handle_list_memo(db, agent.id)
    else:
        return await _handle_unknown(db, agent.id, parsed, utterance)


async def _handle_register(db, agent_id, parsed: ParseResult, raw_input: str) -> str:
    """매물 등록 처리 — MVP에서는 확인 단계 없이 바로 등록 (확인 저장 원칙은 Phase 2)"""

    if parsed.confidence < 0.3:
        return (
            "말씀하신 내용에서 매물 정보를 충분히 파악하지 못했어요.\n"
            "예시: '강남구 역삼동 30평 전세 3억 아파트 등록해줘'"
        )

    # 필수 필드 재질문 (거래 유형)
    if not parsed.transaction_type:
        return (
            "거래 유형을 알려주세요. (매매/전세/월세)\n"
            f"나머지 정보: {_summarize_parsed(parsed)}"
        )

    # MVP: 바로 등록 후 등록 완료 요약 표시
    prop = await create_property_from_parse(db, agent_id, parsed, raw_input)
    summary = format_registered_summary(parsed)
    return f"매물이 등록됐어요!\n\n{summary}\n\n수정이 필요하면 말씀해주세요."


async def _handle_search(db, agent_id, parsed: ParseResult) -> str:
    """매물 검색 처리"""

    # 아무 조건 없이 검색하면 전체 목록
    if not any([
        parsed.transaction_type, parsed.address_gugun,
        parsed.address_dong, parsed.building_name,
        parsed.area_pyeong, parsed.price_main,
    ]):
        properties = await list_properties(db, agent_id)
    else:
        properties = await search_properties(db, agent_id, parsed)

    return format_search_results(properties)


def _handle_update(parsed: ParseResult) -> str:
    """매물 수정 — MVP에서는 안내만"""
    return (
        "매물 수정은 아직 준비 중이에요.\n"
        "수정하시려면 매물을 삭제 후 다시 등록해주세요."
    )


async def _handle_delete(db, agent_id, parsed: ParseResult) -> str:
    """매물 삭제 — 조건에 맞는 매물을 찾아서 삭제"""

    # 조건으로 매물 검색
    matches = await search_properties(db, agent_id, parsed)

    if not matches:
        return "삭제할 매물을 찾지 못했어요. 조건을 다시 확인해주세요."

    if len(matches) == 1:
        prop = matches[0]
        await delete_property(db, agent_id, prop.id)
        return f"매물이 삭제됐어요.\n\n삭제된 매물: {format_property_summary(prop)}"

    # 여러 건이면 목록 보여주고 특정 요청 안내
    lines = [f"조건에 맞는 매물이 {len(matches)}건이에요. 좀 더 구체적으로 알려주세요.\n"]
    for i, prop in enumerate(matches[:5], 1):
        lines.append(f"{i}. {format_property_summary(prop)}")
    return "\n".join(lines)


async def _handle_list_memo(db, agent_id) -> str:
    """저장된 메모 목록 조회"""
    memos = await list_memos(db, agent_id, resolved=False)
    if not memos:
        return "저장된 메모가 없어요."

    lines = [f"저장된 메모 {len(memos)}건이에요.\n"]
    for i, memo in enumerate(memos[:10], 1):
        content_preview = memo.content[:40] + ("..." if len(memo.content) > 40 else "")
        lines.append(f"{i}. {content_preview}")
    return "\n".join(lines)


async def _handle_unknown(db, agent_id, parsed: ParseResult, raw_input: str) -> str:
    """의도 파악 불가 — 메모로 저장 제안"""

    if parsed.clarification_needed:
        return parsed.clarification_needed

    # 메모로 저장
    await create_memo(db, agent_id, MemoCreate(content=raw_input))
    return (
        "말씀하신 내용을 매물 정보로 이해하지 못했어요.\n"
        "메모로 저장해뒀으니, 나중에 다시 정리할 수 있어요.\n\n"
        "매물 등록 예시: '강남구 역삼동 30평 전세 3억 등록해줘'\n"
        "매물 검색 예시: '역삼동 월세 뭐 있어?'"
    )


def _summarize_parsed(parsed: ParseResult) -> str:
    parts = []
    if parsed.address_gugun:
        parts.append(parsed.address_gugun)
    if parsed.address_dong:
        parts.append(parsed.address_dong)
    if parsed.area_pyeong:
        parts.append(f"{parsed.area_pyeong}평")
    if parsed.price_main:
        parts.append(f"{parsed.price_main:,}원")
    if parsed.building_name:
        parts.append(parsed.building_name)
    return ", ".join(parts) if parts else "(추출된 정보 없음)"
