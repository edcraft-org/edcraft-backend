"""Question template schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from edcraft_backend.models.enums import TargetElementType, TargetModifier
from edcraft_backend.utils.code_parser import (
    EntryFunctionParams,
    parse_function_parameters,
)


class CreateTargetElementRequest(BaseModel):
    """Schema for creating a target element associated with a question template."""

    element_type: TargetElementType
    id_list: list[int]
    name: str | None = None
    line_number: int | None = None
    modifier: TargetModifier | None = None


class TargetElementResponse(BaseModel):
    """Schema for target element responses."""

    order: int
    element_type: TargetElementType
    id_list: list[int]
    name: str | None = None
    line_number: int | None = None
    modifier: TargetModifier | None = None

    model_config = ConfigDict(from_attributes=True)


class CreateQuestionTemplateRequest(BaseModel):
    """Schema for creating a new question template."""

    question_type: str
    question_text: str
    description: str | None = None
    code: str
    entry_function: str
    num_distractors: int
    output_type: str
    target_elements: list[CreateTargetElementRequest]


class UpdateQuestionTemplateRequest(BaseModel):
    """Schema for updating a question template."""

    question_type: str | None = None
    question_text: str | None = None
    description: str | None = None
    code: str | None = None
    entry_function: str | None = None
    num_distractors: int | None = None
    output_type: str | None = None
    target_elements: list[CreateTargetElementRequest] | None = None


class QuestionTemplateSummaryResponse(BaseModel):
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
    code: str
    entry_function: str
    num_distractors: int
    output_type: str
    target_elements: list[TargetElementResponse]
    entry_function_params: EntryFunctionParams = EntryFunctionParams(parameters=[])
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def parse_entry_function_params(self) -> "QuestionTemplateResponse":
        """Parse and populate entry_function_params from template_config."""
        self.entry_function_params = parse_function_parameters(
            self.code, self.entry_function
        )
        return self
