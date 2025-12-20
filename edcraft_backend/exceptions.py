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
