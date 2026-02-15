from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class AgentEntity:
    id: UUID
    kakao_user_id: str
    name: str | None = None


@dataclass
class PropertyEntity:
    id: UUID
    agent_id: UUID
    transaction_type: str | None = None
    price_main: int | None = None
    price_monthly: int | None = None
    area_pyeong: float | None = None
    address_sido: str | None = None
    address_gugun: str | None = None
    address_dong: str | None = None
    building_name: str | None = None
    extra: dict = field(default_factory=dict)
    raw_input: str | None = None
    status: str = "active"


@dataclass
class MemoEntity:
    id: UUID
    agent_id: UUID
    content: str
    resolved: bool = False
    created_at: datetime | None = None
