from uuid import UUID

from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
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
    assessment_id: UUID = Field(
        ..., description="Assessment ID to add the question to"
    )
