"""Assessment template schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from edcraft_backend.schemas.question_template import (
    CreateQuestionTemplateRequest,
    QuestionTemplateResponse,
)


class CreateAssessmentTemplateRequest(BaseModel):
    """Schema for creating a new assessment template."""

    owner_id: UUID
    folder_id: UUID
    title: str
    description: str | None = None


class UpdateAssessmentTemplateRequest(BaseModel):
    """Schema for updating an assessment template."""

    title: str | None = None
    description: str | None = None
    folder_id: UUID | None = None


class AssessmentTemplateResponse(BaseModel):
    """Complete schema for assessment template responses."""

    id: UUID
    owner_id: UUID
    folder_id: UUID
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentTemplateQuestionTemplateResponse(QuestionTemplateResponse):
    """Schema for a question template within an assessment template, including order."""

    order: int
    added_at: datetime


class AssessmentTemplateWithQuestionTemplatesResponse(BaseModel):
    """Schema for assessment template with its question templates."""

    id: UUID
    owner_id: UUID
    folder_id: UUID
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    question_templates: list[AssessmentTemplateQuestionTemplateResponse] = []

    model_config = ConfigDict(from_attributes=True)


class InsertQuestionTemplateIntoAssessmentTemplateRequest(BaseModel):
    """Schema for adding a question template to an assessment template."""

    question_template: CreateQuestionTemplateRequest
    order: int | None = None

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: int | None) -> int | None:
        """Validate order is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("order must be >= 0")
        return v


class LinkQuestionTemplateToAssessmentTemplateRequest(BaseModel):
    """Schema for linking an existing question template to an assessment template."""

    question_template_id: UUID
    order: int | None = None

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: int | None) -> int | None:
        """Validate order is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("order must be >= 0")
        return v


class QuestionTemplateOrder(BaseModel):
    """Schema for a single question template order item."""

    question_template_id: UUID
    order: int

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: int) -> int:
        """Validate order is non-negative."""
        if v < 0:
            raise ValueError("order must be >= 0")
        return v


class ReorderQuestionTemplatesInAssessmentTemplateRequest(BaseModel):
    """Schema for reordering question templates in an assessment template."""

    question_template_orders: list[QuestionTemplateOrder]
