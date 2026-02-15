import logging

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://mcp_user:password@localhost:5432/real_estate"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    kakao_bot_id: str = ""
    kakao_skill_secret: str = ""

    # 운영 환경 설정
    environment: str = "development"  # development | staging | production
    log_level: str = "INFO"  # DEBUG | INFO | WARNING | ERROR
    api_key: str = ""  # Properties API 인증용
    cors_origins: list[str] = ["*"]  # CORS 허용 오리진

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """환경변수에서 콤마 구분 문자열을 리스트로 변환"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def check_required_keys(self) -> "Settings":
        if not self.openai_api_key:
            if self.environment == "production":
                raise ValueError(
                    "OPENAI_API_KEY는 운영 환경에서 필수입니다. "
                    "환경변수를 설정하세요."
                )
            logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. AI 파싱 기능이 동작하지 않습니다.")
        if self.environment == "production":
            if "*" in self.cors_origins:
                raise ValueError(
                    "운영 환경에서는 CORS_ORIGINS에 '*'를 사용할 수 없습니다. "
                    "명시적 오리진을 설정하세요."
                )
            if not self.api_key:
                raise ValueError(
                    "운영 환경에서 API_KEY는 필수입니다. "
                    "최소 32자 이상의 랜덤 문자열을 설정하세요."
                )
            if not self.kakao_skill_secret:
                raise ValueError(
                    "운영 환경에서 KAKAO_SKILL_SECRET은 필수입니다."
                )
        return self


settings = Settings()
