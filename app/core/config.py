import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://mcp_user:password@localhost:5432/real_estate"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    kakao_bot_id: str = ""
    kakao_skill_secret: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def check_required_keys(self) -> "Settings":
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. AI 파싱 기능이 동작하지 않습니다.")
        return self


settings = Settings()
