"""Service enums."""

from enum import StrEnum


class ResourceType(StrEnum):
    """Types of resources for cleanup."""

    QUESTIONS = "questions"
    TEMPLATES = "templates"
