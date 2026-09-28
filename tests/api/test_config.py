"""Unit tests for backend configuration settings."""

from api.app.config import Settings, get_settings


def test_default_settings():
    """Verify default settings instantiation and values."""
    settings = Settings()
    assert settings.PROJECT_NAME == "EdgeTwin AI Backend"
    assert settings.API_PORT == 8000
    assert settings.API_V1_PREFIX == "/api/v1"
    assert isinstance(settings.CORS_ORIGINS, list)
    assert "http://localhost:3000" in settings.CORS_ORIGINS


def test_cors_origins_comma_separated_parsing(monkeypatch):
    """Verify string comma-separated CORS origins are parsed into a list."""
    monkeypatch.setenv("CORS_ORIGINS", "http://example.com,https://app.edgetwin.ai")
    settings = Settings()
    assert settings.CORS_ORIGINS == ["http://example.com", "https://app.edgetwin.ai"]


def test_environment_override(monkeypatch):
    """Verify environment variables override default settings."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./custom_test.db")

    settings = Settings()
    assert settings.ENVIRONMENT == "testing"
    assert settings.API_PORT == 9000
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.DATABASE_URL == "sqlite:///./custom_test.db"


def test_get_settings_caching():
    """Verify get_settings returns a cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
