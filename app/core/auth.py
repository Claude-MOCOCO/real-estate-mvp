"""API 키 기반 인증 — Properties API 보호용"""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str:
    """API 키 검증.

    - api_key 설정값이 비어있으면 개발 모드로 간주하여 인증 없이 통과
    - 설정값이 있으면 요청 헤더의 X-API-Key와 비교
    """
    if not settings.api_key:
        return "dev-mode"
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
