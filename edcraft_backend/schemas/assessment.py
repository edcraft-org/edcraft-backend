"""Assessment schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from edcraft_backend.models.enums import CollaboratorRole, ResourceVisibility
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
