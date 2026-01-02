"""Assessment schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from edcraft_backend.schemas.question import QuestionCreate, QuestionResponse


class AssessmentCreate(BaseModel):
    """Schema for creating a new assessment."""

    owner_id: UUID
    folder_id: UUID | None = None
    title: str
    description: str | None = None


class AssessmentUpdate(BaseModel):
    """Schema for updating an assessment."""

    title: str | None = None
    description: str | None = None
    folder_id: UUID | None = None


class AssessmentResponse(BaseModel):
    """Complete schema for assessment responses."""

    id: UUID
    owner_id: UUID
    folder_id: UUID | None
    title: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentQuestionResponse(QuestionResponse):
    """Schema for a question within an assessment, including order."""

    order: int
    added_at: datetime


class AssessmentWithQuestions(BaseModel):
    """Schema for assessment with its questions."""

    id: UUID
    owner_id: UUID
    folder_id: UUID | None
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    questions: list[AssessmentQuestionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AssessmentInsertQuestion(BaseModel):
    """Schema for adding a question to an assessment."""

    question: QuestionCreate
    order: int | None = None

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: int | None) -> int | None:
        """Validate order is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("order must be >= 0")
        return v


class AssessmentLinkQuestion(BaseModel):
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


class AssessmentReorderQuestions(BaseModel):
    """Schema for reordering questions in an assessment."""

    question_orders: list[QuestionOrder]
