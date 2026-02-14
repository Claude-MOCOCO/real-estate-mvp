from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class KakaoUser(BaseModel):
    id: str
    properties: dict = {}


class KakaoUserRequest(BaseModel):
    timezone: str = "Asia/Seoul"
    block: dict = {}
    utterance: str = Field(default="", max_length=1000)
    lang: str = "ko"
    params: dict = {}


class KakaoBot(BaseModel):
    id: str = ""
    name: str = ""


class KakaoAction(BaseModel):
    id: str = ""
    name: str = ""
    params: dict = {}
    detailParams: dict = {}
    clientExtra: dict = {}


class KakaoRequest(BaseModel):
    """카카오 챗봇 스킬 요청"""

    intent: dict = {}
    userRequest: KakaoUserRequest = KakaoUserRequest()
    bot: KakaoBot = KakaoBot()
    action: KakaoAction = KakaoAction()
    callbackUrl: str | None = None

    @field_validator("callbackUrl", mode="before")
    @classmethod
    def validate_callback_url(cls, v):
        if v is None:
            return v
        if not isinstance(v, str) or len(v) > 2048:
            return None
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return None  # 유효하지 않은 URL은 무시하고 직접 응답 모드로 전환
        # 내부 네트워크 SSRF 방지
        host = parsed.hostname or ""
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or host.startswith("10.") or host.startswith("192.168.") or host.startswith("172."):
            return None
        return v


class KakaoSimpleText(BaseModel):
    text: str


class KakaoOutput(BaseModel):
    simpleText: KakaoSimpleText | None = None


class KakaoTemplate(BaseModel):
    outputs: list[KakaoOutput] = []


class KakaoResponse(BaseModel):
    """카카오 챗봇 스킬 응답"""

    version: str = "2.0"
    useCallback: bool | None = None
    template: KakaoTemplate = KakaoTemplate()

    @classmethod
    def text(cls, message: str, use_callback: bool = False) -> "KakaoResponse":
        return cls(
            useCallback=True if use_callback else None,
            template=KakaoTemplate(
                outputs=[KakaoOutput(simpleText=KakaoSimpleText(text=message))]
            ),
        )

    @classmethod
    def callback_pending(cls, utterance: str = "") -> "KakaoResponse":
        """콜백 대기 응답 — 발화 내용에 따라 맞춤 대기 메시지"""
        # 발화 내용 기반으로 대기 메시지 결정
        lower = utterance.strip()
        if any(kw in lower for kw in ("등록", "추가", "넣어", "올려")):
            message = "매물 등록 중이에요... 잠시만요!"
        elif any(kw in lower for kw in ("찾아", "검색", "조회", "있어", "뭐 있")):
            message = "매물을 찾고 있어요... 곧 알려드릴게요!"
        elif any(kw in lower for kw in ("삭제", "지워", "빼")):
            message = "매물을 확인하고 있어요..."
        elif any(kw in lower for kw in ("메모", "저장")):
            message = "메모를 확인하고 있어요..."
        else:
            message = "잠시만요, 확인 중입니다..."

        return cls(
            useCallback=True,
            template=KakaoTemplate(
                outputs=[
                    KakaoOutput(
                        simpleText=KakaoSimpleText(text=message)
                    )
                ]
            ),
        )
