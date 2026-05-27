from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai 이력서 첨삭"
    app_env: str = "development"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_resume_review"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    mock_ai_mode: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    admin_emails: list[str] = Field(default_factory=list)
    free_daily_review_limit: int = 3
    free_daily_refine_limit: int = 10
    free_monthly_pdf_export_limit: int = 5
    pro_daily_review_limit: int = 100
    pro_daily_refine_limit: int = 300
    pro_monthly_pdf_export_limit: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
