"""FastAPI 의존성 주입 팩토리 — 유스케이스에 포트 구현체를 바인딩

헥사고날 아키텍처에서 '조립(Composition Root)' 역할.
어댑터 → 포트 바인딩은 여기서만 발생하며,
유스케이스와 도메인 코드는 구체 구현을 전혀 모른다.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.openai_parser import openai_parser
from app.adapters.sqlalchemy_repository import (
    SQLAlchemyAgentRepository,
    SQLAlchemyMemoRepository,
    SQLAlchemyPropertyRepository,
)
from app.application.use_cases import AssistantUseCase, PropertyUseCase
from app.core.database import get_db


def get_assistant_use_case(
    db: AsyncSession = Depends(get_db),
) -> AssistantUseCase:
    """AssistantUseCase 팩토리 — 카카오 스킬 엔드포인트용"""
    return AssistantUseCase(
        agent_repo=SQLAlchemyAgentRepository(db),
        property_repo=SQLAlchemyPropertyRepository(db),
        memo_repo=SQLAlchemyMemoRepository(db),
        parser=openai_parser,
    )


def get_property_use_case(
    db: AsyncSession = Depends(get_db),
) -> PropertyUseCase:
    """PropertyUseCase 팩토리 — Properties CRUD API용"""
    return PropertyUseCase(
        property_repo=SQLAlchemyPropertyRepository(db),
    )
