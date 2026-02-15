"""AI 파싱 모듈 — 하위 호환성 래퍼 (어댑터 계층으로 위임)

기존 import 경로를 유지하면서 내부적으로 OpenAI 어댑터를 사용합니다.
테스트에서 _client를 직접 설정하는 패턴도 지원합니다.
"""

import json
import logging

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.adapters.openai_parser import SYSTEM_PROMPT, openai_parser
from app.core.config import settings
from app.schemas.property import ParseResult

logger = logging.getLogger(__name__)


class PropertyParser:
    """하위 호환성을 위한 래퍼 클래스.

    기본 동작은 openai_parser 어댑터에 위임하되,
    테스트에서 _client를 직접 주입하는 패턴을 지원합니다.
    """

    def __init__(self):
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        # _client가 직접 설정된 경우 (테스트) 그것을 사용
        if self._client is not None:
            return self._client
        # 그렇지 않으면 어댑터의 client 사용
        return openai_parser.client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        reraise=True,
    )
    async def _call_openai(self, user_input: str):
        """OpenAI API 호출 (일시적 오류 시 최대 3회 재시도)"""
        return await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
            timeout=10,
        )

    async def parse(self, user_input: str) -> ParseResult:
        # _client가 직접 설정된 경우 (테스트) 자체 로직으로 처리
        if self._client is not None:
            return await self._parse_with_own_client(user_input)
        # 그렇지 않으면 어댑터에 위임
        return await openai_parser.parse(user_input)

    async def _parse_with_own_client(self, user_input: str) -> ParseResult:
        """_client가 직접 설정된 경우의 파싱 로직 (테스트 호환)"""
        content = None
        try:
            response = await self._call_openai(user_input)

            if not response.choices:
                logger.error("AI 응답에 choices가 비어있습니다")
                raise ValueError("AI 응답이 비어있습니다")

            content = response.choices[0].message.content
            if not content:
                raise ValueError("AI 응답이 비어있습니다")
            data = json.loads(content)
            return ParseResult(**data)

        except json.JSONDecodeError:
            logger.error("AI 파싱 결과 JSON 디코딩 실패: %s", content[:200] if content else "None")
            return ParseResult(
                intent="unknown",
                confidence=0.0,
                clarification_needed="말씀하신 내용을 이해하지 못했어요. 다시 한번 말씀해주시겠어요?",
            )
        except Exception as e:
            logger.error("AI 파싱 오류: type=%s, detail=%s", type(e).__name__, e)
            return ParseResult(
                intent="unknown",
                confidence=0.0,
                clarification_needed="잠시 오류가 발생했어요. 다시 시도해주세요.",
            )


# 기존 호환성 유지: 모듈 레벨 parser 인스턴스
parser = PropertyParser()
