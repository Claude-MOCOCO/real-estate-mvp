"""하위 호환성 래퍼 — 기존 테스트의 patch 경로 유지

모든 비즈니스 로직은 application/use_cases.py의 AssistantUseCase에 있으며,
이 모듈은 기존 함수 시그니처(handle_utterance)와 상수를 re-export한다.
"""

from app.application.use_cases import (  # noqa: F401
    CONFIDENCE_THRESHOLD,
    MAX_DELETE_OPTIONS,
    MAX_MEMO_DISPLAY,
    MEMO_PREVIEW_LENGTH,
    AssistantUseCase,
    _summarize_parsed,
)
from app.domain.services.responder import (  # noqa: F401
    format_price,
    format_property_summary,
    format_registered_summary,
    format_search_results,
)
