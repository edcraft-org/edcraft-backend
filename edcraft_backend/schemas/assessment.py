"""Assessment schemas for request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from edcraft_backend.models.enums import (
    CollaboratorRole,
    ResourceType,
    ResourceVisibility,
)
from edcraft_backend.schemas.question import (
    CreateQuestionRequest,
    QuestionResponse,
)


class CreateAssessmentRequest(BaseModel):
    """Schema for creating a new assessment."""

    folder_id: UUID
    title: str
    description: str | None = None


class UpdateAssessmentRequest(BaseModel):
    """Schema for updating an assessment."""

    title: str | None = None
    description: str | None = None
    folder_id: UUID | None = None
    visibility: ResourceVisibility | None = None


class AssessmentResponse(BaseModel):
    """Complete schema for assessment responses."""

    id: UUID
    owner_id: UUID
    folder_id: UUID
    title: str
    description: str
    visibility: ResourceVisibility
    created_at: datetime
    updated_at: datetime
    my_role: CollaboratorRole | None = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentWithQuestionsResponse(BaseModel):
    """Schema for assessment with its questions."""

    id: UUID
    owner_id: UUID
    folder_id: UUID
    title: str
    description: str | None
    visibility: ResourceVisibility
    created_at: datetime
    updated_at: datetime
    questions: list[QuestionResponse] = []
    my_role: CollaboratorRole | None = None

    model_config = ConfigDict(from_attributes=True)


class InsertQuestionIntoAssessmentRequest(BaseModel):
    """Schema for adding a question to an assessment."""

    question: CreateQuestionRequest
    order: int | None = None

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: int | None) -> int | None:
        """Validate order is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("order must be >= 0")
        return v


class LinkQuestionToAssessmentRequest(BaseModel):
    """Schema for linking an existing question to an assessment."""

    question_id: UUID
    order: int | None = None

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: int | None) -> int | None:
        """Validate order is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("order must be >= 0")
        return v


class QuestionOrder(BaseModel):
    """Schema for a single question order item."""

    question_id: UUID
    order: int

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: int) -> int:
        """Validate order is non-negative."""
        if v < 0:
            raise ValueError("order must be >= 0")
        return v


class ReorderQuestionsInAssessmentRequest(BaseModel):
    """Schema for reordering questions in an assessment."""

    question_orders: list[QuestionOrder]


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
