from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "个人工作助理 Agent 平台"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://127.0.0.1:5432/myagent"
    auth_secret: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_urlsafe(48)))
    access_token_ttl_minutes: int = 480
    admin_username: str = "admin"
    admin_password: SecretStr | None = None
    knowledge_base_url: str = "http://127.0.0.1:8010"
    knowledge_timeout_seconds: float = 30.0
    ark_api_key: SecretStr | None = None
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    agent_model: str = "doubao-seed-2-1-pro-260628"
    agent_max_iters: int = 8
    agent_temperature: float | None = 0.3
    agent_max_tokens: int | None = 4096
    openai_api_key: SecretStr | None = None
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
