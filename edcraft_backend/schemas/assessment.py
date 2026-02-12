"""Assessment schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from edcraft_backend.schemas.question import (
    CreateQuestionRequest,
    MCQResponse,
    MRQResponse,
    ShortAnswerResponse,
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


class AssessmentResponse(BaseModel):
    """Complete schema for assessment responses."""

    id: UUID
    owner_id: UUID
    folder_id: UUID
    title: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentMCQResponse(MCQResponse):
    """Response schema for MCQ question in assessment context."""

    order: int
    added_at: datetime


class AssessmentMRQResponse(MRQResponse):
    """Response schema for MRQ question in assessment context."""

    order: int
    added_at: datetime


class AssessmentShortAnswerResponse(ShortAnswerResponse):
    """Response schema for short answer question in assessment context."""

    order: int
    added_at: datetime


AssessmentQuestionResponse = (
    AssessmentMCQResponse | AssessmentMRQResponse | AssessmentShortAnswerResponse
)


class AssessmentWithQuestionsResponse(BaseModel):
    """Schema for assessment with its questions."""

    id: UUID
    owner_id: UUID
    folder_id: UUID
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    questions: list[AssessmentQuestionResponse] = []

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
