"""Question schemas for request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreateQuestionRequest(BaseModel):
    """Schema for creating a new question."""

    template_id: UUID | None = None
    question_type: str
    question_text: str
    additional_data: dict[str, Any] = {}


class UpdateQuestionRequest(BaseModel):
    """Schema for updating a question."""

    question_type: str | None = None
    question_text: str | None = None
    additional_data: dict[str, Any] | None = None


class QuestionResponse(BaseModel):
    """Complete schema for question responses."""

    id: UUID
    owner_id: UUID
    template_id: UUID | None
    question_type: str
    question_text: str
    additional_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
