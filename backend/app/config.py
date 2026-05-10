"""Centralized settings loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "dev"

    # LLM - accept both LLM_MODEL and OPENAI_MODEL env names
    llm_provider: str = "openai"
    llm_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("LLM_MODEL", "OPENAI_MODEL"),
    )
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Embeddings
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./data/finsight.db"
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "financial_knowledge"

    # Cache
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    # Auth - accept both JWT_EXPIRE_MINUTES and JWT_EXPIRES_IN env names
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(
        default=1440,
        validation_alias=AliasChoices("JWT_EXPIRE_MINUTES", "JWT_EXPIRES_IN"),
    )

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # CORS - frontend dev server + n8n
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:5678",
            "http://127.0.0.1:5173",
        ]
    )

    # Paths
    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def knowledge_dir(self) -> Path:
        return self.project_root / "data" / "knowledge"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
