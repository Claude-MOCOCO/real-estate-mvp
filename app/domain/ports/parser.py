from abc import ABC, abstractmethod

from app.domain.value_objects import ParseResult


class ParserPort(ABC):
    @abstractmethod
    async def parse(self, user_input: str) -> ParseResult: ...
