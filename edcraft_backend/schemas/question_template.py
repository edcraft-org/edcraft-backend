"""Question template schemas for request/response validation."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from edcraft_backend.models.enums import (
    TargetElementType,
    TargetModifier,
    TextTemplateType,
)
from edcraft_backend.schemas.code_info import CodeInfo
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
    argument_keys: list[str] | None = None


class TargetElementResponse(BaseModel):
    """Schema for target element responses."""

    order: int
    element_type: TargetElementType
    id_list: list[int]
    name: str | None = None
    line_number: int | None = None
    modifier: TargetModifier | None = None
    argument_keys: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class CreateQuestionTemplateRequest(BaseModel):
    """Schema for creating a new question template."""

    question_type: str
    question_text_template: str
    text_template_type: TextTemplateType
    description: str | None = None
    code: str
    entry_function: str
    num_distractors: int
    output_type: str
    target_elements: list[CreateTargetElementRequest]
    input_data_config: dict[str, dict] | None = None
    code_info: CodeInfo | None = None

    @model_validator(mode="after")
    def validate_basic_template_variables(self) -> CreateQuestionTemplateRequest:
        """For basic templates, validate all {var} placeholders are valid entry function params."""
        if self.text_template_type != TextTemplateType.BASIC:
            return self

        # Extract all {var} placeholders from the template
        template_vars = set(re.findall(r"\{(\w+)\}", self.question_text_template))
        if not template_vars:
            return self

        # Parse valid parameter names from the entry function
        params = parse_function_parameters(self.code, self.entry_function)

        valid_params = set(params.parameters)
        invalid_vars = template_vars - valid_params
        if invalid_vars:
            raise ValueError(
                f"Basic template contains invalid variable(s): {invalid_vars}. "
                f"Valid parameters are: {valid_params}"
            )

        return self


class UpdateQuestionTemplateRequest(BaseModel):
    """Schema for updating a question template."""

    question_type: str | None = None
    question_text_template: str | None = None
    text_template_type: TextTemplateType | None = None
    description: str | None = None
    code: str | None = None
    entry_function: str | None = None
    num_distractors: int | None = None
    output_type: str | None = None
    target_elements: list[CreateTargetElementRequest] | None = None
    input_data_config: dict[str, dict] | None = None
    code_info: CodeInfo | None = None


class QuestionTemplateSummaryResponse(BaseModel):
    """Lightweight schema for listing question templates."""

    id: UUID
    owner_id: UUID
    question_type: str
    question_text_template: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionTemplateResponse(BaseModel):
    """Complete schema for question template responses."""

    id: UUID
    owner_id: UUID
    question_type: str
    question_text_template: str
    text_template_type: TextTemplateType
    description: str | None = None
    code: str
    entry_function: str
    num_distractors: int
    output_type: str
    target_elements: list[TargetElementResponse]
    input_data_config: dict[str, dict] | None = None
    code_info: CodeInfo | None = None
    entry_function_params: EntryFunctionParams = EntryFunctionParams(parameters=[])
    linked_from_template_id: UUID | None
    assessment_template_id: UUID | None
    question_template_bank_id: UUID | None
    order: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def parse_entry_function_params(self) -> QuestionTemplateResponse:
        """Parse and populate entry_function_params from template_config."""
        self.entry_function_params = parse_function_parameters(
            self.code, self.entry_function
        )
        return self
