"""하위 호환성 래퍼 — 기존 테스트의 import 경로 유지

매물 CRUD 로직은 application/use_cases.py의 PropertyUseCase와
adapters/sqlalchemy_repository.py에 있다.
"""

from app.adapters.sqlalchemy_repository import _escape_like  # noqa: F401
