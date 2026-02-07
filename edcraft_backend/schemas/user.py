"""User schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class CreateUserRequest(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr
    name: str


class UpdateUserRequest(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = None
    name: str | None = None


class UserSummaryResponse(BaseModel):
    """Lightweight schema for listing users."""

    id: UUID
    email: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Complete schema for user responses."""

    id: UUID
    email: str
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
