"""Question template bank schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from edcraft_backend.schemas.question_template import (
    CreateQuestionTemplateRequest,
    QuestionTemplateResponse,
)


class CreateQuestionTemplateBankRequest(BaseModel):
    """Schema for creating a new question template bank."""

    folder_id: UUID
    title: str
    description: str | None = None


class UpdateQuestionTemplateBankRequest(BaseModel):
    """Schema for updating a question template bank."""

    title: str | None = None
    description: str | None = None
    folder_id: UUID | None = None


class QuestionTemplateBankResponse(BaseModel):
    """Complete schema for question template bank responses."""

    id: UUID
    owner_id: UUID
    folder_id: UUID
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionTemplateBankQuestionTemplateResponse(QuestionTemplateResponse):
    """Response schema for question template in question template bank context."""

    added_at: datetime


class QuestionTemplateBankWithTemplatesResponse(BaseModel):
    """Schema for question template bank with its question templates."""

    id: UUID
    owner_id: UUID
    folder_id: UUID
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    question_templates: list[QuestionTemplateBankQuestionTemplateResponse] = []

    model_config = ConfigDict(from_attributes=True)


class InsertQuestionTemplateIntoQuestionTemplateBankRequest(BaseModel):
    """Schema for adding a question template to a question template bank."""

    question_template: CreateQuestionTemplateRequest


class LinkQuestionTemplateToQuestionTemplateBankRequest(BaseModel):
    """Schema for linking an existing question template to a question template bank."""

    question_template_id: UUID
