import json
import logging

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.schemas.property import ParseResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 부동산 매물 정보를 구조화하는 전문가입니다.
공인중개사가 자연어로 입력한 내용에서 매물 정보를 추출하세요.

## 추출 필드

- intent: "register" | "search" | "update" | "delete" | "list_memo" | "unknown"
- transaction_type: "매매" | "전세" | "월세" | null
- price_main: 숫자(원 단위) | null  (매매가, 전세금, 월세 보증금)
- price_monthly: 숫자(원 단위, 월세일 때만) | null
- area_pyeong: 숫자 | null
- address_sido: 시/도 | null
- address_gugun: 구/군 | null
- address_dong: 동/읍/면 | null
- building_name: 건물명/아파트명 | null
- extra: { 층수, 방수, 화장실수, 주차, 특이사항 등 기타 정보 }
- missing_fields: 필수인데 추출 못한 필드명 리스트
- confidence: 0.0 ~ 1.0 (전체 파싱 신뢰도)
- clarification_needed: 사용자에게 다시 물어볼 내용 | null

## 금액 변환 규칙

- "3천" = 30,000,000원 (3천만원)
- "3억" = 300,000,000원
- "3억 5천" = 350,000,000원
- "500/50" = 보증금 5,000,000원 / 월세 500,000원
- "1000/80" = 보증금 10,000,000원 / 월세 800,000원
- 단위 생략 시 부동산 관행 기준으로 추론 (아파트 매매 → 만원 단위, 월세 → 만원 단위)

## 의도(intent) 판단 규칙

- "등록", "추가", "넣어", "올려" 등 → register
- "찾아", "검색", "조회", "있어?", "뭐 있어" 등 → search
- "수정", "바꿔", "변경" 등 → update
- "삭제", "지워", "빼" 등 → delete
- "메모", "메모 보여줘", "저장된 메모" 등 → list_memo
- 판단 불가 → unknown

## 응답 형식

반드시 JSON만 반환하세요. 다른 텍스트 없이 JSON 객체만.

## 예시

입력: "강남구 역삼동 30평대 전세 3억 아파트 등록해줘"
출력:
{
  "intent": "register",
  "transaction_type": "전세",
  "price_main": 300000000,
  "price_monthly": null,
  "area_pyeong": 30,
  "address_sido": "서울",
  "address_gugun": "강남구",
  "address_dong": "역삼동",
  "building_name": null,
  "extra": {},
  "missing_fields": ["building_name"],
  "confidence": 0.85,
  "clarification_needed": "건물명(아파트명)을 알려주시면 더 정확히 등록할 수 있어요."
}"""


class PropertyParser:
    def __init__(self):
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._client

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


parser = PropertyParser()
