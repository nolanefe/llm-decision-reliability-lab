from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "LLM Decision Reliability Lab"
    environment: str = "development"
    database_url: str = "sqlite:///./reliability_lab.db"
    openai_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
