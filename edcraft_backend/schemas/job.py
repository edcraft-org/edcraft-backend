"""Schemas for async job submission and polling."""

from uuid import UUID

from edcraft_engine.question_generator.models import Question
from pydantic import BaseModel

from edcraft_backend.schemas.assessment import AssessmentWithQuestionsResponse
from edcraft_backend.schemas.input_generator import GenerateInputsResponse
from edcraft_backend.schemas.question_generation import (
    CodeAnalysisResponse,
    TemplatePreviewResponse,
)

type JobResult = (
    CodeAnalysisResponse
    | TemplatePreviewResponse
    | Question
    | GenerateInputsResponse
    | AssessmentWithQuestionsResponse
)


class JobSubmittedResponse(BaseModel):
    """Returned immediately when a job is submitted to Nomad."""

    job_id: UUID
    status_url: str


class JobStatusResponse(BaseModel):
    """Returned by GET /jobs/{job_id} — current status and result when available."""

    job_id: UUID
    status: str
    result: JobResult | None = None
    error: str | None = None


class JobCallbackPayload(BaseModel):
    """Payload POSTed by the Nomad worker to /jobs/callback/{token}."""

    result: str | None = None  # JSON-serialized result string
    error: str | None = None
