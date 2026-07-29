from functools import lru_cache

from pydantic import field_validator
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
    openai_request_timeout_seconds: float = 60.0
    max_runs_per_experiment: int = 30
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    @field_validator("openai_api_key")
    @classmethod
    def _blank_key_is_unavailable(cls, value: str | None) -> str | None:
        """A key that is unset or blank (e.g. ``OPENAI_API_KEY=`` with no
        value) must be indistinguishable from "not configured" -- normalize
        it to ``None`` here so every reader gets one unambiguous signal."""
        if value is None:
            return None
        return value.strip() or None

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
