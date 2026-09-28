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

    # MQTT Broker Configuration (T-032 MQTT Ingestion Service)
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None
    MQTT_TLS: bool = False
    MQTT_CLIENT_ID: str = "edgetwin-ingest"
    MQTT_RECONNECT_MIN_DELAY: int = 1
    MQTT_RECONNECT_MAX_DELAY: int = 30

    # MLflow tracking
    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"

    # Security and Authentication (T-038)
    JWT_SECRET_KEY: str = "edgetwin-dev-secret-key-do-not-use-in-production-12345678"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        origins: list[str]
        if isinstance(v, str) and not v.startswith("["):
            origins = [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = [str(i).strip() for i in v if str(i).strip()]
        elif isinstance(v, str):
            origins = [v.strip()]
        else:
            raise ValueError(f"Invalid CORS_ORIGINS format: {v}")

        if "*" in origins:
            raise ValueError(
                "Wildcard CORS origin '*' is prohibited when credentials and authentication are enabled."
            )
        return origins


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
