from typing import Any
from uuid import UUID

from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    Question,
    QuestionSpec,
)
from pydantic import BaseModel, Field

from edcraft_backend.schemas.code_info import CodeInfo
from edcraft_backend.schemas.form_builder import FormElement


class CodeAnalysisRequest(BaseModel):
    """Request model for code analysis."""

    code: str = Field(..., description="The code to be analysed")


class CodeAnalysisResponse(BaseModel):
    """Response model for code analysis. Contains code information and form schema."""

    code_info: CodeInfo = Field(
        ..., description="Code structure and elements information"
    )
    form_elements: list[FormElement] = Field(..., description="List of form elements")


class QuestionGenerationRequest(BaseModel):
    """Request to generate a question based on form selections."""

    code: str = Field(..., description="Original algorithm source code")
    question_spec: QuestionSpec = Field(
        ..., description="Specifications for the question to be generated"
    )
    execution_spec: ExecutionSpec = Field(
        ..., description="Specifications for code execution"
    )
    generation_options: GenerationOptions = Field(
        ..., description="Options for question generation"
    )


class GenerateIntoAssessmentRequest(BaseModel):
    """Request to generate a question and add it to an assessment."""

    assessment_id: UUID = Field(..., description="Assessment ID to add the question to")
    owner_id: UUID = Field(..., description="Owner ID for the new question")
    code: str = Field(..., description="Original algorithm source code")
    question_spec: QuestionSpec = Field(
        ..., description="Specifications for the question to be generated"
    )
    execution_spec: ExecutionSpec = Field(
        ..., description="Specifications for code execution"
    )
    generation_options: GenerationOptions = Field(
        ..., description="Options for question generation"
    )


class GenerateFromTemplateRequest(BaseModel):
    """Request to generate a question from a template."""

    owner_id: UUID = Field(..., description="Owner ID for the new question")
    code: str = Field(..., description="Original algorithm source code")
    assessment_id: UUID = Field(..., description="Assessment ID to add the question to")


class GenerateQuestionFromTemplateRequest(BaseModel):
    """Generate question from template (no DB persistence)."""

    input_data: dict[str, Any] = Field(
        ..., description="Input data dict for ExecutionSpec"
    )


class AssessmentMetadata(BaseModel):
    """Metadata for assessment creation from template."""

    owner_id: UUID = Field(..., description="Owner ID for the assessment")
    folder_id: UUID | None = Field(None, description="Optional folder ID")
    title: str | None = Field(
        None, description="Override assessment title (defaults to template title)"
    )
    description: str | None = Field(
        None,
        description="Override assessment description (defaults to template description)",
    )


class GenerateAssessmentFromTemplateRequest(BaseModel):
    """Generate assessment from template (with DB persistence)."""

    assessment_metadata: AssessmentMetadata = Field(
        ...,
        description="Metadata for the assessment to be created from the template",
    )
    question_inputs: list[dict[str, Any]] = Field(
        ...,
        description="Array of input_data dicts, in question template order",
    )


class GenerateTemplateRequest(BaseModel):
    """Request to generate a question template (no DB persistence)."""

    code: str = Field(..., description="Algorithm code")
    entry_function: str = Field(..., description="Name of the entry function")
    question_spec: QuestionSpec = Field(
        ..., description="Specifications for the question to be generated"
    )
    generation_options: GenerationOptions = Field(
        ..., description="Options for question generation"
    )


class TemplatePreviewResponse(BaseModel):
    """Response for template preview."""

    question_text: str = Field(..., description="Generated template question text")
    question_type: str = Field(..., description="Type of question")
    template_config: dict[str, Any] = Field(
        ..., description="Template configuration for future use"
    )
    preview_question: Question = Field(
        ..., description="Preview with placeholders"
    )
