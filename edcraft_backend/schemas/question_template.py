"""Question template schemas for request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from edcraft_engine.question_generator.models import (
    GenerationOptions,
    QuestionSpec,
)
from pydantic import BaseModel, ConfigDict, model_validator

from edcraft_backend.utils.code_parser import (
    EntryFunctionParams,
    parse_function_parameters,
)


class QuestionTemplateConfig(BaseModel):
    """Schema for question template configuration."""

    code: str
    question_spec: QuestionSpec
    generation_options: GenerationOptions
    entry_function: str


class CreateQuestionTemplateRequest(BaseModel):
    """Schema for creating a new question template."""

    question_type: str
    question_text: str
    description: str | None = None
    template_config: QuestionTemplateConfig


class UpdateQuestionTemplateRequest(BaseModel):
    """Schema for updating a question template."""

    question_type: str | None = None
    question_text: str | None = None
    description: str | None = None
    template_config: QuestionTemplateConfig | None = None


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
    template_config: dict[str, Any]
    entry_function_params: EntryFunctionParams = EntryFunctionParams(parameters=[])
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def parse_entry_function_params(self) -> "QuestionTemplateResponse":
        """Parse and populate entry_function_params from template_config."""
        code = self.template_config.get("code", "")
        entry_function = self.template_config.get("entry_function", "")
        self.entry_function_params = parse_function_parameters(code, entry_function)
        return self
