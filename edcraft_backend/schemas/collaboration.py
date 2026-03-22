"""Shared collaboration schemas for collaborator management across all resources."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from edcraft_backend.models.enums import CollaboratorRole, ResourceType


class CollaboratorResponse(BaseModel):
    """Response schema for a collaborator entry."""

    id: UUID
    resource_type: ResourceType
    resource_id: UUID
    user_name: str
    user_email: str
    role: CollaboratorRole
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_user_fields(cls, data: Any) -> Any:
        """Flatten user name/email from the eagerly-loaded user relationship."""
        if hasattr(data, "user") and data.user is not None:
            return {
                "id": data.id,
                "resource_type": data.resource_type,
                "resource_id": data.resource_id,
                "user_name": data.user.name,
                "user_email": data.user.email,
                "role": data.role,
                "added_at": data.added_at,
            }
        return data


class AddCollaboratorRequest(BaseModel):
    """Request body for adding a collaborator."""

    email: EmailStr
    role: CollaboratorRole

    @field_validator("role")
    @classmethod
    def role_cannot_be_owner(cls, v: CollaboratorRole) -> CollaboratorRole:
        """Prevent directly assigning the owner role."""
        if v == CollaboratorRole.OWNER:
            raise ValueError("Cannot manually assign the 'owner' role.")
        return v


class UpdateCollaboratorRoleRequest(BaseModel):
    """Request body for updating a collaborator's role."""

    role: CollaboratorRole
