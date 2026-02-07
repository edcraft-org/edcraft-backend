"""Auth schemas for request/response validation."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Enforce the configured minimum password length from settings."""
        from edcraft_backend.config import settings

        if len(v) < settings.password_min_length:
            raise ValueError(
                f"Password must be at least {settings.password_min_length} characters"
            )
        return v


class LoginRequest(BaseModel):
    """Schema for email login."""

    email: EmailStr
    password: str


class TokenPairResponse(BaseModel):
    """JWT token pair containing access token and refresh token."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int  # seconds until access token expires


class AuthUserResponse(BaseModel):
    """User profile returned after registration or GET /auth/me."""

    id: UUID
    email: str
    name: str

    model_config = ConfigDict(from_attributes=True)
