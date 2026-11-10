from functools import lru_cache
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "ScopeProof API"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://scopeproof:scopeproof@localhost:5433/scopeproof"

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Public URL of the web app (used for links that point back into the UI).
    FRONTEND_URL: str = "http://localhost:3000"

    # Document uploads
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_MB: int = 25  # per uploaded file (a ZIP counts as one file)
    MAX_ZIP_ENTRIES: int = 200
    MAX_EXTRACTED_MB: int = 50  # total uncompressed size allowed from one ZIP

    # Pluggable engines. The placeholders keep the flow working until the real
    # implementations land. See app/services/analysis and app/services/payments.
    ANALYZER: str = "placeholder"  # "placeholder" | "rag"
    ASTRO_GATEWAY_URL: str = ""
    ASTRO_GATEWAY_API_KEY: SecretStr = SecretStr("")
    RAG_MODEL: str = "gpt-5-6-luna"
    RAG_EMBEDDING_MODEL: str = "titan-embed-text-v2"
    RAG_TOP_K: int = 32
    RAG_MAX_CHUNKS: int = 150
    RAG_MAX_ITEMS: int = 20
    RAG_REQUEST_TIMEOUT_SECONDS: float = 45
    RAG_TOTAL_TIMEOUT_SECONDS: float = 240

    PAYMENT_PROVIDER: str = "placeholder"  # "placeholder" | "paypal"

    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
