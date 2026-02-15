from abc import ABC, abstractmethod


class CallbackPort(ABC):
    @abstractmethod
    async def send(self, callback_url: str, response_data: dict) -> None: ...
