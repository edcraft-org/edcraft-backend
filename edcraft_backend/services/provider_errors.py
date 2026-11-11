"""Sanitized provider-connection errors shared by endpoint and persistence."""

from __future__ import annotations

from edcraft_backend.exceptions import EdCraftBaseException


class ProviderConnectionError(EdCraftBaseException):
    """Base class for sanitized provider-connection errors."""


class ProviderConnectionNotFound(ProviderConnectionError):
    """The connection is unknown or owned by another user."""

    def __init__(self, message: str = "Model connection not found.") -> None:
        super().__init__(message, 404)


class ProviderConnectionInvalid(ProviderConnectionError):
    """The supplied connection settings cannot be used."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 422)


class ProviderConnectionUnavailable(ProviderConnectionError):
    """The provider could not be contacted or rejected the key."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 502)


__all__ = [
    "ProviderConnectionError",
    "ProviderConnectionInvalid",
    "ProviderConnectionNotFound",
    "ProviderConnectionUnavailable",
]
