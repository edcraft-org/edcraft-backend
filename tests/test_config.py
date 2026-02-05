"""Tests for configuration module."""

import pytest

from edcraft_backend.config import Environment, Settings, get_project_root, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """Clear the settings cache before each test."""
    get_settings.cache_clear()


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Settings default values (with auto-enabled database echo in development)."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("APP_NAME", "EdCraft Backend API")

    settings = Settings()

    assert settings.app.env == Environment.DEVELOPMENT
    assert settings.app.name == "EdCraft Backend API"
    assert settings.is_development is True
    assert settings.is_production is False
    assert settings.is_test is False


def test_database_echo_auto_enable_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that database_echo is True in development when DATABASE_ECHO not set."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.delenv("DATABASE_ECHO", raising=False)

    settings = Settings()

    assert settings.database.echo is True
    assert settings.is_development is True


def test_settings_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Settings in production mode."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

    settings = Settings()

    assert settings.app.env == Environment.PRODUCTION
    assert settings.is_production is True
    assert settings.is_development is False


def test_settings_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Settings in test mode."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test_db")

    settings = Settings()

    assert settings.is_test is True
    assert str(settings.database.url) == "postgresql+asyncpg://test:test@localhost/test_db"


def test_settings_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that settings are case insensitive."""
    monkeypatch.setenv("app_env", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

    settings = Settings()

    assert settings.app.env == Environment.PRODUCTION


def test_cors_origins_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CORS origins as list."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000","https://example.com"]')

    settings = Settings()

    assert len(settings.cors.origins) == 2
    assert "http://localhost:3000" in settings.cors.origins
    assert "https://example.com" in settings.cors.origins


def test_database_url_string_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that database_url can be converted to string."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://dev:dev@localhost/dev_db")

    settings = Settings()

    assert str(settings.database.url) == "postgresql+asyncpg://dev:dev@localhost/dev_db"


def test_database_echo_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that explicit database_echo setting is respected."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("DATABASE_ECHO", "false")

    settings = Settings()

    assert settings.database.echo is False


def test_get_project_root() -> None:
    """Test that get_project_root finds the correct project root."""
    root = get_project_root()

    assert (root / "pyproject.toml").exists()
    assert (root / "edcraft_backend").exists()
    assert root.is_absolute()
    assert root.name == "edcraft-backend"
