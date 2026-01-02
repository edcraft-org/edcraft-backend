"""Service enums."""

from enum import Enum


class ResourceType(str, Enum):
    """Types of resources for cleanup."""

    QUESTIONS = "questions"
    TEMPLATES = "templates"
