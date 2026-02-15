"""매물 서비스 — 하위 호환성 래퍼 (어댑터 계층으로 위임)

기존 import 경로를 유지하면서 내부적으로 SQLAlchemy 어댑터를 사용합니다.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.sqlalchemy_repository import (
    SQLAlchemyAgentRepository,
    SQLAlchemyMemoRepository,
    SQLAlchemyPropertyRepository,
    _escape_like,
)
from app.schemas.property import MemoCreate, ParseResult, PropertyCreate, PropertyStatus, PropertyUpdate

logger = logging.getLogger(__name__)

# 검색 상수 (하위 호환성 유지)
SEARCH_MAX_RESULTS = 20
PRICE_MARGIN_RATIO = 0.2
AREA_MARGIN_PYEONG = 5.0

# _escape_like는 어댑터에서 import하여 re-export
__all__ = [
    "_escape_like",
    "get_or_create_agent",
    "create_property",
    "create_property_from_parse",
    "list_properties",
    "get_property",
    "update_property",
    "delete_property",
    "search_properties",
    "create_memo",
    "list_memos",
]


async def get_or_create_agent(db: AsyncSession, kakao_user_id: str):
    """카카오 사용자 ID로 Agent 조회 또는 생성 (race condition 방어)"""
    repo = SQLAlchemyAgentRepository(db)
    return await repo.get_or_create(kakao_user_id)


async def create_property(db: AsyncSession, agent_id: uuid.UUID, data: PropertyCreate):
    repo = SQLAlchemyPropertyRepository(db)
    return await repo.create(agent_id, data)


async def create_property_from_parse(
    db: AsyncSession, agent_id: uuid.UUID, parsed: ParseResult, raw_input: str
):
    """파싱 결과로 매물 생성"""
    repo = SQLAlchemyPropertyRepository(db)
    return await repo.create_from_parse(agent_id, parsed, raw_input)


async def list_properties(
    db: AsyncSession,
    agent_id: uuid.UUID,
    transaction_type: str | None = None,
    address_gugun: str | None = None,
    status: str = PropertyStatus.ACTIVE.value,
    limit: int = 50,
    offset: int = 0,
):
    """매물 목록 조회 (개인화 격리: agent_id 필수, 페이지네이션 적용)"""
    repo = SQLAlchemyPropertyRepository(db)
    return await repo.list_by_agent(
        agent_id, transaction_type, address_gugun, status, limit, offset
    )


async def get_property(
    db: AsyncSession, agent_id: uuid.UUID, property_id: uuid.UUID
):
    """매물 단건 조회 (개인화 격리)"""
    repo = SQLAlchemyPropertyRepository(db)
    return await repo.get(agent_id, property_id)


async def update_property(
    db: AsyncSession,
    agent_id: uuid.UUID,
    property_id: uuid.UUID,
    data: PropertyUpdate,
):
    repo = SQLAlchemyPropertyRepository(db)
    return await repo.update(agent_id, property_id, data)


async def delete_property(
    db: AsyncSession, agent_id: uuid.UUID, property_id: uuid.UUID
) -> bool:
    """소프트 삭제"""
    repo = SQLAlchemyPropertyRepository(db)
    return await repo.delete(agent_id, property_id)


async def search_properties(
    db: AsyncSession, agent_id: uuid.UUID, parsed: ParseResult
):
    """파싱 결과 기반 매물 검색"""
    repo = SQLAlchemyPropertyRepository(db)
    return await repo.search(agent_id, parsed)


async def create_memo(
    db: AsyncSession, agent_id: uuid.UUID, data: MemoCreate
):
    """메모 생성. 반환: (memo, is_new) -- is_new=False면 중복 스킵됨"""
    repo = SQLAlchemyMemoRepository(db)
    return await repo.create(agent_id, data)


async def list_memos(
    db: AsyncSession, agent_id: uuid.UUID, resolved: bool = False, limit: int = 50
):
    repo = SQLAlchemyMemoRepository(db)
    return await repo.list_by_agent(agent_id, resolved, limit)
