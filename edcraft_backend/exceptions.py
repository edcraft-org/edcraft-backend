"""Custom exceptions for the EdCraft backend."""

from fastapi import status


class EdCraftBaseException(Exception):
    """Base exception for all EdCraft exceptions."""

    def __init__(
        self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class CodeDecodingError(EdCraftBaseException):
    """Raised when code cannot be decoded from unicode escape sequences."""

    def __init__(self, message: str = "Failed to decode code input") -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class CodeAnalysisError(EdCraftBaseException):
    """Raised when code analysis fails."""

    def __init__(self, message: str = "Failed to analyze code") -> None:
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)


class QuestionGenerationError(EdCraftBaseException):
    """Raised when question generation fails."""

    def __init__(self, message: str = "Failed to generate question") -> None:
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)


# Domain-specific exceptions


class ResourceNotFoundError(EdCraftBaseException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class DuplicateResourceError(EdCraftBaseException):
    """Raised when attempting to create a duplicate resource."""

    def __init__(self, resource_type: str, field: str, value: str) -> None:
        message = f"{resource_type} with {field} '{value}' already exists"
        super().__init__(message, status.HTTP_409_CONFLICT)


class UnauthorizedAccessError(EdCraftBaseException):
    """Raised when a user attempts to access a resource they don't own."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        message = f"Unauthorized access to {resource_type} with ID {resource_id}"
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ValidationError(EdCraftBaseException):
    """Raised when validation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class CircularReferenceError(EdCraftBaseException):
    """Raised when a circular reference is detected in folder hierarchy."""

    def __init__(
        self, message: str = "Circular reference detected in folder hierarchy"
    ) -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class ForbiddenOperationError(EdCraftBaseException):
    """Raised when an operation is not allowed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN)


# Auth exceptions


class TokenDecodeError(Exception):
    """Failed to decode JWT."""

    pass


class AuthenticationError(EdCraftBaseException):
    """Invalid credentials."""

    def __init__(self, message: str = "Invalid credentials") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class InvalidTokenError(EdCraftBaseException):
    """Invalid or expired token."""

    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AccountInactiveError(EdCraftBaseException):
    """Account is inactive."""

    def __init__(self) -> None:
        super().__init__("Account is inactive", status.HTTP_403_FORBIDDEN)


class EmailSendError(EdCraftBaseException):
    """Failed to send email."""

    def __init__(self, message: str = "Failed to send email") -> None:
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)
