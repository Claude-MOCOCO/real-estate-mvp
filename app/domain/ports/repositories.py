from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import AgentEntity, MemoEntity, PropertyEntity
from app.domain.value_objects import MemoCreate, ParseResult


class AgentRepository(ABC):
    @abstractmethod
    async def get_or_create(self, kakao_user_id: str) -> AgentEntity: ...


class PropertyRepository(ABC):
    @abstractmethod
    async def create_from_parse(
        self, agent_id: UUID, parsed: ParseResult, raw_input: str
    ) -> PropertyEntity: ...

    @abstractmethod
    async def create(self, agent_id: UUID, data) -> PropertyEntity: ...

    @abstractmethod
    async def list_by_agent(
        self,
        agent_id: UUID,
        transaction_type: str | None = None,
        address_gugun: str | None = None,
        status: str = "active",
        limit: int = 50,
        offset: int = 0,
    ) -> list[PropertyEntity]: ...

    @abstractmethod
    async def get(self, agent_id: UUID, property_id: UUID) -> PropertyEntity | None: ...

    @abstractmethod
    async def update(
        self, agent_id: UUID, property_id: UUID, data
    ) -> PropertyEntity | None: ...

    @abstractmethod
    async def delete(self, agent_id: UUID, property_id: UUID) -> bool: ...

    @abstractmethod
    async def search(
        self, agent_id: UUID, parsed: ParseResult
    ) -> list[PropertyEntity]: ...


class MemoRepository(ABC):
    @abstractmethod
    async def create(
        self, agent_id: UUID, data: MemoCreate
    ) -> tuple[MemoEntity, bool]: ...

    @abstractmethod
    async def list_by_agent(
        self, agent_id: UUID, resolved: bool = False, limit: int = 50
    ) -> list[MemoEntity]: ...
