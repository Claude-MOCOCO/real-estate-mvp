"""개인비서 핵심 유스케이스 — 포트(추상)에만 의존, 구체적 구현체를 모름

헥사고날 아키텍처의 Application 계층으로,
도메인 포트(AgentRepository, PropertyRepository, MemoRepository, ParserPort)를
주입받아 비즈니스 흐름을 오케스트레이션한다.
"""

import logging
from uuid import UUID

from app.domain.ports.repositories import AgentRepository, PropertyRepository, MemoRepository
from app.domain.ports.parser import ParserPort
from app.domain.value_objects import ParseResult, MemoCreate
from app.services.responder import (
    format_price,
    format_property_summary,
    format_registered_summary,
    format_search_results,
)

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.3
MAX_DELETE_OPTIONS = 5
MEMO_PREVIEW_LENGTH = 40
MAX_MEMO_DISPLAY = 10


class AssistantUseCase:
    """개인비서 핵심 유스케이스 — 포트에만 의존, 구체적 구현체를 모름"""

    def __init__(
        self,
        agent_repo: AgentRepository,
        property_repo: PropertyRepository,
        memo_repo: MemoRepository,
        parser: ParserPort,
    ):
        self.agent_repo = agent_repo
        self.property_repo = property_repo
        self.memo_repo = memo_repo
        self.parser = parser

    async def handle_utterance(self, kakao_user_id: str, utterance: str) -> str:
        agent = await self.agent_repo.get_or_create(kakao_user_id)
        parsed = await self.parser.parse(utterance)

        logger.info(
            "파싱 결과: intent=%s, confidence=%.2f, user=%s",
            parsed.intent, parsed.confidence, kakao_user_id,
        )
        logger.info("핸들러 진입: intent=%s, agent=%s", parsed.intent, agent.id)

        if parsed.intent == "register":
            return await self._handle_register(agent.id, parsed, utterance)
        elif parsed.intent == "search":
            return await self._handle_search(agent.id, parsed)
        elif parsed.intent == "update":
            return self._handle_update(parsed)
        elif parsed.intent == "delete":
            return await self._handle_delete(agent.id, parsed)
        elif parsed.intent == "list_memo":
            return await self._handle_list_memo(agent.id)
        else:
            return await self._handle_unknown(agent.id, parsed, utterance)

    async def _handle_register(self, agent_id: UUID, parsed: ParseResult, raw_input: str) -> str:
        if parsed.confidence < CONFIDENCE_THRESHOLD:
            return (
                "말씀하신 내용에서 매물 정보를 충분히 파악하지 못했어요.\n"
                "예시: '강남구 역삼동 30평 전세 3억 아파트 등록해줘'"
            )
        if not parsed.transaction_type:
            return (
                "거래 유형을 알려주세요. (매매/전세/월세)\n"
                f"나머지 정보: {_summarize_parsed(parsed)}"
            )
        prop = await self.property_repo.create_from_parse(agent_id, parsed, raw_input)
        summary = format_registered_summary(parsed)
        return f"매물이 등록됐어요!\n\n{summary}\n\n수정이 필요하면 말씀해주세요."

    async def _handle_search(self, agent_id: UUID, parsed: ParseResult) -> str:
        is_full_list = not any([
            parsed.transaction_type, parsed.address_gugun,
            parsed.address_dong, parsed.building_name,
            parsed.area_pyeong, parsed.price_main,
        ])
        if is_full_list:
            properties = await self.property_repo.list_by_agent(agent_id)
        else:
            properties = await self.property_repo.search(agent_id, parsed)
        logger.info("검색 결과: %d건, agent=%s", len(properties), agent_id)
        return format_search_results(properties, is_full_list=is_full_list)

    def _handle_update(self, parsed: ParseResult) -> str:
        return (
            "매물 수정은 아직 준비 중이에요.\n"
            "수정하시려면 매물을 삭제 후 다시 등록해주세요."
        )

    async def _handle_delete(self, agent_id: UUID, parsed: ParseResult) -> str:
        matches = await self.property_repo.search(agent_id, parsed)
        logger.info("삭제 대상 검색: %d건, agent=%s", len(matches), agent_id)

        if not matches:
            return "삭제할 매물을 찾지 못했어요. 조건을 다시 확인해주세요."

        if len(matches) == 1:
            prop = matches[0]
            await self.property_repo.delete(agent_id, prop.id)
            return f"매물이 삭제됐어요.\n\n삭제된 매물: {format_property_summary(prop)}"

        lines = [f"조건에 맞는 매물이 {len(matches)}건이에요. 좀 더 구체적으로 알려주세요.\n"]
        for i, prop in enumerate(matches[:MAX_DELETE_OPTIONS], 1):
            lines.append(f"{i}. {format_property_summary(prop)}")
        if len(matches) > MAX_DELETE_OPTIONS:
            lines.append(f"\n(외 {len(matches) - MAX_DELETE_OPTIONS}건 — 조건을 더 구체적으로 입력해주세요)")
        return "\n".join(lines)

    async def _handle_list_memo(self, agent_id: UUID) -> str:
        memos = await self.memo_repo.list_by_agent(agent_id, resolved=False)
        if not memos:
            return "저장된 메모가 없어요."

        lines = [f"저장된 메모 {len(memos)}건이에요.\n"]
        for i, memo in enumerate(memos[:MAX_MEMO_DISPLAY], 1):
            content_preview = memo.content[:MEMO_PREVIEW_LENGTH] + ("..." if len(memo.content) > MEMO_PREVIEW_LENGTH else "")
            lines.append(f"{i}. {content_preview}")
        if len(memos) > MAX_MEMO_DISPLAY:
            lines.append(f"\n(외 {len(memos) - MAX_MEMO_DISPLAY}건 더 있음)")
        return "\n".join(lines)

    async def _handle_unknown(self, agent_id: UUID, parsed: ParseResult, raw_input: str) -> str:
        if parsed.clarification_needed:
            return parsed.clarification_needed

        _memo, is_new = await self.memo_repo.create(agent_id, MemoCreate(content=raw_input))

        if is_new:
            return (
                "말씀하신 내용을 매물 정보로 이해하지 못했어요.\n"
                "메모로 저장해뒀으니, 나중에 다시 정리할 수 있어요.\n\n"
                "매물 등록 예시: '강남구 역삼동 30평 전세 3억 등록해줘'\n"
                "매물 검색 예시: '역삼동 월세 뭐 있어?'"
            )
        else:
            return (
                "같은 내용이 이미 메모에 저장돼 있어요.\n"
                "메모 확인: '저장된 메모 보여줘'\n\n"
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
        parts.append(format_price(parsed.price_main))
    if parsed.building_name:
        parts.append(parsed.building_name)
    return ", ".join(parts) if parts else "(추출된 정보 없음)"
