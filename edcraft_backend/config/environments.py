"""Environment configuration enums."""

from enum import Enum


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"
