"""Configuration module for EdCraft Backend."""

from edcraft_backend.config.environments import Environment
from edcraft_backend.config.settings import (
    Settings,
    get_project_root,
    get_settings,
    settings,
)

__all__ = [
    "Environment",
    "Settings",
    "get_project_root",
    "get_settings",
    "settings",
]
