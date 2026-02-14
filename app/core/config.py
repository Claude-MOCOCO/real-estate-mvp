from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://mcp_user:password@localhost:5432/real_estate"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    kakao_bot_id: str = ""
    kakao_skill_secret: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
