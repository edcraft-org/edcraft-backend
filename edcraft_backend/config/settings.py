"""Application settings using Pydantic BaseSettings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, PostgresDsn, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from edcraft_backend.config.environments import Environment


class Settings(BaseSettings):
    """
    Application settings with environment-based configuration.

    Configuration is loaded in the following order (later overrides earlier):
    1. .env.{APP_ENV} (environment-specific)
    2. .env.local (local overrides)
    3. System environment variables (highest priority)
    """

    # Application settings
    app_env: Environment = Field(
        default=Environment.DEVELOPMENT, description="Application environment"
    )

    app_name: str = Field(default="EdCraft Backend API", description="Application name")

    app_version: str = Field(default="0.1.0", description="Application version")

    # Database settings
    database_url: PostgresDsn | None = Field(
        default=None, description="PostgreSQL database URL (required via environment)"
    )

    database_echo: bool | None = Field(default=None, description="Echo SQL queries to logs")

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins",
    )

    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS requests"
    )

    # Server settings
    server_host: str = Field(default="127.0.0.1", description="Server host")

    server_port: int = Field(default=5000, description="Server port")

    log_level: str = Field(default="info", description="Logging level")

    model_config = SettingsConfigDict(
        # Don't automatically load from .env
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def validate_database_url(cls, v: PostgresDsn | None) -> PostgresDsn:
        """Ensure database_url is provided via environment variables."""
        if v is None:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Set it in your .env.{APP_ENV} file or as a system environment variable."
            )
        return v

    @field_validator("database_echo", mode="before")
    @classmethod
    def set_database_echo(cls, v: Any, info: ValidationInfo) -> bool:
        """Auto-enable database echo in development if not explicitly set."""
        if v is not None:
            if isinstance(v, str):
                return v.lower() in ("true", "1", "yes", "on")
            return bool(v)
        # Default to True in development, False otherwise
        env = info.data.get("app_env", Environment.DEVELOPMENT)
        return bool(env == Environment.DEVELOPMENT)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.app_env == Environment.TEST


def get_project_root() -> Path:
    """
    Find project root by looking for pyproject.toml.

    Returns:
        Path to project root directory

    Raises:
        RuntimeError: If project root cannot be found
    """
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find project root (no pyproject.toml found)")


def load_env_files(app_env: str | None = None) -> None:
    """
    Load environment files in the correct order.

    Load order (later overrides earlier):
    1. .env.{APP_ENV} (environment-specific configuration)
    2. .env.local (local overrides)
    3. System environment variables (highest priority)

    Args:
        app_env: Application environment. If None, reads from APP_ENV env var.
    """
    from dotenv import load_dotenv

    project_root = get_project_root()
    env = app_env or os.getenv("APP_ENV", "development")

    env_file = project_root / f".env.{env}"
    if env_file.exists():
        load_dotenv(env_file, override=False)

    local_env = project_root / ".env.local"
    if local_env.exists():
        load_dotenv(local_env, override=True)


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This function is cached to ensure we only load settings once.
    Use this function throughout the application to access settings.

    Returns:
        Settings instance
    """
    load_env_files()
    return Settings()


settings = get_settings()
