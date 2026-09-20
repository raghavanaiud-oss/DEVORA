from typing import List, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CodeOrbit"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    
    # Security / Auth
    SECRET_KEY: str = "super-secret-codeorbit-jwt-production-grade-key-change-in-prod-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/codeorbit"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/codeorbit"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Execution Sandbox
    EXECUTION_SANDBOX_TYPE: str = "process"  # "docker" or "process"
    EXECUTION_TIMEOUT_SECONDS: int = 10
    EXECUTION_MAX_MEMORY_MB: int = 128
    EXECUTION_MAX_OUTPUT_BYTES: int = 100000  # 100 KB
    
    # AI & Embeddings
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    AI_PROVIDER: str = "codeorbit_engine"  # "openai", "gemini", "anthropic", "codeorbit_engine"
    EMBEDDING_DIMENSION: int = 384
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
