from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_id: int = Field(alias="ADMIN_ID")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/postgres",
        alias="DATABASE_URL",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
