import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Novel-to-Webtoon Studio"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key-studio-insecure-only-for-local"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    
    # Persistence
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/studio.db"
    STORAGE_LOCAL_DIR: str = "./storage"
    
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

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
