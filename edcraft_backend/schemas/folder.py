"""Folder schemas for request/response validation."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from edcraft_backend.schemas.assessment import AssessmentResponse
    from edcraft_backend.schemas.assessment_template import AssessmentTemplateResponse


class FolderCreate(BaseModel):
    """Schema for creating a new folder."""

    owner_id: UUID
    parent_id: UUID | None = None
    name: str
    description: str | None = None


class FolderUpdate(BaseModel):
    """Schema for updating a folder."""

    name: str | None = None
    description: str | None = None


class FolderMove(BaseModel):
    """Schema for moving a folder to a different parent."""

    parent_id: UUID | None


class FolderList(BaseModel):
    """Lightweight schema for listing folders."""

    id: UUID
    owner_id: UUID
    parent_id: UUID | None
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


class FolderTree(BaseModel):
    """Schema for folder tree structure with nested children."""

    id: UUID
    owner_id: UUID
    parent_id: UUID | None
    name: str
    description: str | None
    created_at: datetime
    children: list["FolderTree"] = []

    model_config = ConfigDict(from_attributes=True)


class FolderPath(BaseModel):
    """Schema for folder path from root to current folder."""

    path: list[FolderList]

    model_config = ConfigDict(from_attributes=True)


class FolderWithContents(BaseModel):
    """Schema for folder with its contents (assessments and templates)."""

    id: UUID
    owner_id: UUID
    parent_id: UUID | None
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    assessments: list["AssessmentResponse"] = []
    assessment_templates: list["AssessmentTemplateResponse"] = []

    model_config = ConfigDict(from_attributes=True)
