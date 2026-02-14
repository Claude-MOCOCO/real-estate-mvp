from pydantic import BaseModel, Field


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
    def callback_pending(cls) -> "KakaoResponse":
        """콜백 대기 응답 — 비동기 처리 시작"""
        return cls(
            useCallback=True,
            template=KakaoTemplate(
                outputs=[
                    KakaoOutput(
                        simpleText=KakaoSimpleText(
                            text="잠시만요, 확인 중입니다..."
                        )
                    )
                ]
            ),
        )
