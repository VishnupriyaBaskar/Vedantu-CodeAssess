from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_DIR = Path(__file__).resolve().parents[3]
_ENV_PATH = _ROOT_DIR / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Vedantu Coding Assessment Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    API_VERSION: str = "v1"
    API_V1_STR: str = "/api/v1"

    # Server binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Allowlist
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Judge0 Community Edition Settings (Stage 2.5)
    JUDGE0_URL: str = "http://127.0.0.1:2358"
    JUDGE0_AUTHN_HEADER: str = "X-Auth-Token"
    JUDGE0_AUTHN_TOKEN: str = ""
    JUDGE0_TIMEOUT_SECONDS: float = 10.0
    JUDGE0_MAX_POLL_RETRIES: int = 20
    JUDGE0_POLL_INTERVAL_SECONDS: float = 0.5

    # Internal Development Security
    INTERNAL_DEV_SECRET: str = ""
    ENABLE_DEV_JUDGE0_ROUTES: bool = True

    # Database Configuration (Stage 2.6 - PostgreSQL 16)
    POSTGRES_SERVER: str = "127.0.0.1"
    POSTGRES_USER: str = "vedantu_admin"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "vedantu_assessment_db"
    DATABASE_URL: Optional[str] = None

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: float = 30.0
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    # Redis In-Memory Cache & Session Broker (Stage 2.4 / Stage 3)
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # JWT Authentication & RBAC Configuration (Stage 3)
    JWT_SECRET_KEY: str = "dev_secret_key_minimum_32_characters_long_for_security_vedantu_platform"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "vedantu-assessment-platform"
    JWT_AUDIENCE: str = "vedantu-assessment-users"

    # AI Evaluation & Static Analysis Configuration (Stage 5)
    AI_EVALUATION_ENABLED: bool = True
    AI_PROVIDER: str = "mock"  # "mock" | "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    AI_REQUEST_TIMEOUT_SECONDS: float = 15.0

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
            return self.DATABASE_URL
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
            return self.DATABASE_URL
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(
        env_file=(_ENV_PATH, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()