"""Environment configuration enums."""

from enum import StrEnum


class Environment(StrEnum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"
