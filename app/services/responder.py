"""하위 호환성 래퍼 — 기존 테스트의 import 경로 유지

실제 구현은 domain/services/responder.py에 있다.
"""

from app.domain.services.responder import (  # noqa: F401
    format_price,
    format_property_summary,
    format_registered_summary,
    format_search_results,
)
