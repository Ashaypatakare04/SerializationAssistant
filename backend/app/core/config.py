import os
from typing import List, Any, Union, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Novel-to-Webtoon Studio"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key-studio-insecure-only-for-local"
    
    # CORS
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("[") and v.strip().endswith("]"):
                try:
                    import json
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v
    
    # Persistence & Storage
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/studio.db"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            # Guard against unexpanded Railway template references
            if v.startswith("${{") or v.startswith("${"):
                raise ValueError(
                    f"DATABASE_URL contains an unexpanded variable template: '{v}'. "
                    f"In Railway, your database service is named 'webtoon-postgres', "
                    f"so reference '${{{{webtoon-postgres.DATABASE_URL}}}}' instead."
                )
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    STORAGE_LOCAL_DIR: str = "./storage"
    STORAGE_BACKEND: str = "local"  # "local", "s3"
    S3_BUCKET_NAME: str = ""
    S3_ENDPOINT_URL: Optional[str] = None
    S3_REGION_NAME: str = "us-east-1"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    
    # AI Providers
    LLM_PROVIDER: str = "mock"  # "mock", "gemini", "openai", "anthropic"
    IMAGE_PROVIDER: str = "mock"  # "mock", "stability", "openai", "local"
    
    # API Keys
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    STABILITY_API_KEY: str = ""
    LOCAL_DIFFUSION_ENDPOINT: str = "http://127.0.0.1:7860"
    
    # Job Engine
    MAX_CONCURRENT_JOBS: int = 4
    WORKER_POLL_INTERVAL_SECONDS: float = 1.0
    STANDALONE_WORKER: bool = False

    # Security & Quota Limits
    MAX_DAILY_GENERATIONS_PER_PROJECT: int = 100

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
