"""httpx 기반 콜백 구현 (헥사고날 아키텍처 어댑터 계층)"""

import httpx

from app.domain.ports.callback import CallbackPort


class HttpxCallbackAdapter(CallbackPort):
    async def send(self, callback_url: str, response_data: dict) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(callback_url, json=response_data)
