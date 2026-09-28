"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """EdgeTwin AI Backend Settings."""

    # Project metadata
    PROJECT_NAME: str = "EdgeTwin AI Backend"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Server configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # CORS configuration
    CORS_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Database configuration (Defaulting to PostgreSQL, supports SQLite for local dev/testing)
    DATABASE_URL: str = "postgresql+psycopg2://edgetwin:edgetwin_dev_secret@localhost:5432/edgetwin"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    # MQTT Broker Configuration (for future ingest service T-032)
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None
    MQTT_TLS: bool = False

    # MLflow tracking
    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(f"Invalid CORS_ORIGINS format: {v}")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
