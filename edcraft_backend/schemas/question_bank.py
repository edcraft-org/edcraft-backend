"""Question bank schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from edcraft_backend.models.enums import CollaboratorRole, ResourceVisibility
from edcraft_backend.schemas.question import (
    CreateQuestionRequest,
    QuestionResponse,
)


class CreateQuestionBankRequest(BaseModel):
    """Schema for creating a new question bank."""

    folder_id: UUID
    title: str
    description: str | None = None


class UpdateQuestionBankRequest(BaseModel):
    """Schema for updating a question bank."""

    title: str | None = None
    description: str | None = None
    folder_id: UUID | None = None
    visibility: ResourceVisibility | None = None


class QuestionBankResponse(BaseModel):
    """Complete schema for question bank responses."""

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


class QuestionBankWithQuestionsResponse(BaseModel):
    """Schema for question bank with its questions."""

    id: UUID
    owner_id: UUID
    folder_id: UUID
    title: str
    description: str
    visibility: ResourceVisibility
    created_at: datetime
    updated_at: datetime
    questions: list[QuestionResponse] = []
    my_role: CollaboratorRole | None = None

    model_config = ConfigDict(from_attributes=True)


class InsertQuestionIntoQuestionBankRequest(BaseModel):
    """Schema for adding a question to a question bank."""

    question: CreateQuestionRequest


class LinkQuestionToQuestionBankRequest(BaseModel):
    """Schema for linking an existing question to a question bank."""

    question_id: UUID
