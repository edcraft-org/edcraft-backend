"""Folder schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from edcraft_backend.schemas.assessment import AssessmentResponse
from edcraft_backend.schemas.assessment_template import AssessmentTemplateResponse
from edcraft_backend.schemas.question_bank import QuestionBankResponse


class CreateFolderRequest(BaseModel):
    """Schema for creating a new folder."""

    parent_id: UUID
    name: str
    description: str | None = None


class UpdateFolderRequest(BaseModel):
    """Schema for updating a folder."""

    name: str | None = None
    description: str | None = None


class MoveFolderRequest(BaseModel):
    """Schema for moving a folder to a different parent."""

    parent_id: UUID


class FolderResponse(BaseModel):
    """Complete schema for folder responses."""

    id: UUID
    owner_id: UUID
    parent_id: UUID | None
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FolderTreeResponse(BaseModel):
    """Schema for folder tree structure with nested children."""

    id: UUID
    owner_id: UUID
    parent_id: UUID | None
    name: str
    description: str | None
    created_at: datetime
    children: list["FolderTreeResponse"] = []

    model_config = ConfigDict(from_attributes=True)


class FolderPathResponse(BaseModel):
    """Schema for folder path from root to current folder."""

    path: list[FolderResponse]

    model_config = ConfigDict(from_attributes=True)


class FolderWithContentsResponse(BaseModel):
    """Schema for folder with its contents (assessments, templates, and child folders)."""

    id: UUID
    owner_id: UUID
    parent_id: UUID | None
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    assessments: list["AssessmentResponse"] = []
    assessment_templates: list["AssessmentTemplateResponse"] = []
    question_banks: list["QuestionBankResponse"] = []
    folders: list["FolderResponse"] = []

    model_config = ConfigDict(from_attributes=True)
