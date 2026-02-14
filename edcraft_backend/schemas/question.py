"""Question schemas for request/response validation."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

if TYPE_CHECKING:
    from edcraft_backend.schemas.assessment import AssessmentResponse
    from edcraft_backend.schemas.question_bank import QuestionBankResponse


# Data schemas for different question types
class MCQData(BaseModel):
    """Multiple Choice Question data."""

    options: list[str] = Field(..., min_length=2, max_length=10)
    correct_index: int = Field(..., ge=0)

    @field_validator("correct_index")
    @classmethod
    def validate_correct_index(cls, v: int, info: ValidationInfo) -> int:
        """Validate that correct_index is within options range."""
        options = info.data.get("options", [])
        if v >= len(options):
            raise ValueError("correct_index must be a valid option index")
        return v

    model_config = ConfigDict(from_attributes=True)


class MRQData(BaseModel):
    """Multiple Response Question data."""

    options: list[str] = Field(..., min_length=2, max_length=10)
    correct_indices: list[int] = Field(..., min_length=1)

    @field_validator("correct_indices")
    @classmethod
    def validate_indices(cls, v: list[int], info: ValidationInfo) -> list[int]:
        """Validate that all indices are within options range."""
        options = info.data.get("options", [])
        if any(idx >= len(options) or idx < 0 for idx in v):
            raise ValueError("All correct_indices must be valid option indices")
        return v

    model_config = ConfigDict(from_attributes=True)


class ShortAnswerData(BaseModel):
    """Short Answer Question data."""

    correct_answer: str = Field(..., min_length=1, max_length=5000)

    model_config = ConfigDict(from_attributes=True)


# Create question request schemas
class BaseCreateQuestionRequest(BaseModel):
    """Base schema for creating a question."""

    template_id: UUID | None = None
    question_text: str = Field(..., min_length=1, max_length=5000)


class CreateMCQRequest(BaseCreateQuestionRequest):
    """Schema for creating a new MCQ question."""

    question_type: Literal["mcq"] = "mcq"
    data: MCQData


class CreateMRQRequest(BaseCreateQuestionRequest):
    """Schema for creating a new MRQ question."""

    question_type: Literal["mrq"] = "mrq"
    data: MRQData


class CreateShortAnswerRequest(BaseCreateQuestionRequest):
    """Schema for creating a new short answer question."""

    question_type: Literal["short_answer"] = "short_answer"
    data: ShortAnswerData


CreateQuestionRequest = CreateMCQRequest | CreateMRQRequest | CreateShortAnswerRequest


# Update question request schema
class UpdateQuestionRequest(BaseModel):
    """Schema for updating any question type."""

    question_type: Literal["mcq", "mrq", "short_answer"] | None = None
    question_text: str | None = Field(None, min_length=1, max_length=5000)
    data: MCQData | MRQData | ShortAnswerData | None = None


# Response schemas
class BaseQuestionResponse(BaseModel):
    """Base schema for question response."""

    id: UUID
    owner_id: UUID
    template_id: UUID | None
    question_text: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MCQResponse(BaseQuestionResponse):
    """Response schema for MCQ question."""

    question_type: Literal["mcq"]
    mcq_data: MCQData


class MRQResponse(BaseQuestionResponse):
    """Response schema for MRQ question."""

    question_type: Literal["mrq"]
    mrq_data: MRQData


class ShortAnswerResponse(BaseQuestionResponse):
    """Response schema for short answer question."""

    question_type: Literal["short_answer"]
    short_answer_data: ShortAnswerData


QuestionResponse = MCQResponse | MRQResponse | ShortAnswerResponse


class QuestionUsageResponse(BaseModel):
    """Response schema for question usage information."""

    assessments: list[AssessmentResponse] = []
    question_banks: list[QuestionBankResponse] = []

    model_config = ConfigDict(from_attributes=True)
