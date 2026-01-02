"""Question template schemas for request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from edcraft_engine.question_generator.models import (
    GenerationOptions,
    QuestionSpec,
)
from pydantic import BaseModel, ConfigDict


class QuestionTemplateConfig(BaseModel):
    """Schema for question template configuration."""

    code: str
    question_spec: QuestionSpec
    generation_options: GenerationOptions
    entry_function: str


class QuestionTemplateCreate(BaseModel):
    """Schema for creating a new question template."""

    owner_id: UUID
    question_type: str
    question_text: str
    description: str | None = None
    template_config: QuestionTemplateConfig


class QuestionTemplateUpdate(BaseModel):
    """Schema for updating a question template."""

    question_type: str | None = None
    question_text: str | None = None
    description: str | None = None
    template_config: QuestionTemplateConfig | None = None


class QuestionTemplateList(BaseModel):
    """Lightweight schema for listing question templates."""

    id: UUID
    owner_id: UUID
    question_type: str
    question_text: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionTemplateResponse(BaseModel):
    """Complete schema for question template responses."""

    id: UUID
    owner_id: UUID
    question_type: str
    question_text: str
    description: str | None = None
    template_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
