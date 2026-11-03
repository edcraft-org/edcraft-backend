"""Owner-scoped AI authoring endpoints for issues 48-50."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, status

from edcraft_backend.dependencies import AiAuthoringServiceDep, CurrentUserDep
from edcraft_backend.schemas.ai_authoring import (
    ApprovalRequest,
    ApprovalResponse,
    AuthoringCapabilitiesResponse,
    AuthoringJobStatusResponse,
    AuthoringJobSubmittedResponse,
    AuthoringJobSummary,
    AuthoringReviewResponse,
    ErrorResponse,
    GeneratedQuestionsBatch,
    GenerateRequest,
    PreviewRequest,
    PreviewResponse,
    SubmitAuthoringJobRequest,
)

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not signed in."},
    404: {"model": ErrorResponse, "description": "Unknown or unowned job."},
    409: {"model": ErrorResponse, "description": "Stale or unusable artifact."},
    429: {"model": ErrorResponse, "description": "Authoring admission is full."},
}

router = APIRouter(
    prefix="/ai-authoring",
    tags=["ai-authoring"],
    responses=_ERROR_RESPONSES,
)


@router.get("/capabilities", response_model=AuthoringCapabilitiesResponse)
async def get_capabilities(
    user: CurrentUserDep,
    service: AiAuthoringServiceDep,
) -> AuthoringCapabilitiesResponse:
    """Return enabled domains and safe configured model display metadata."""
    return await service.capabilities()


@router.post(
    "/jobs",
    response_model=AuthoringJobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_job(
    payload: SubmitAuthoringJobRequest,
    user: CurrentUserDep,
    service: AiAuthoringServiceDep,
) -> AuthoringJobSubmittedResponse:
    """Admit one authoring job and return its polling URL."""
    job = await service.submit(user.id, payload)
    return AuthoringJobSubmittedResponse(
        job_id=job.job_id,
        status_url=f"/ai-authoring/jobs/{job.job_id}",
    )


@router.get("/jobs", response_model=list[AuthoringJobSummary])
async def list_jobs(
    user: CurrentUserDep,
    service: AiAuthoringServiceDep,
) -> list[AuthoringJobSummary]:
    """Return recent jobs owned by the signed-in user."""
    jobs = await service.list_jobs(user.id)
    return [service.job_summary(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=AuthoringJobStatusResponse)
async def get_job(
    job_id: UUID,
    user: CurrentUserDep,
    service: AiAuthoringServiceDep,
) -> AuthoringJobStatusResponse:
    """Poll one owned job without exposing the internal report."""
    job = await service.get_job(user.id, job_id)
    return service.job_status(job)


@router.get("/jobs/{job_id}/review", response_model=AuthoringReviewResponse)
async def review_job(
    job_id: UUID,
    user: CurrentUserDep,
    service: AiAuthoringServiceDep,
) -> AuthoringReviewResponse:
    """Return safe prompt, plan, attempts, findings and exact artifact identity."""
    return await service.review(user.id, job_id)


@router.post("/jobs/{job_id}/preview", response_model=PreviewResponse)
async def preview_job(
    job_id: UUID,
    payload: PreviewRequest,
    user: CurrentUserDep,
    service: AiAuthoringServiceDep,
) -> PreviewResponse:
    """Generate one deterministic draft locally from a checked artifact."""
    return await service.preview(user.id, job_id, payload.seed)


@router.post("/jobs/{job_id}/approval", response_model=ApprovalResponse)
async def decide_job(
    job_id: UUID,
    payload: ApprovalRequest,
    user: CurrentUserDep,
    service: AiAuthoringServiceDep,
) -> ApprovalResponse:
    """Approve or reject the exact artifact digest shown during review."""
    return await service.decide(user.id, job_id, payload)


@router.post("/jobs/{job_id}/generate", response_model=GeneratedQuestionsBatch)
async def generate_job(
    job_id: UUID,
    payload: GenerateRequest,
    user: CurrentUserDep,
    service: AiAuthoringServiceDep,
) -> GeneratedQuestionsBatch:
    """Return deterministic consecutive questions from an approved artifact."""
    return await service.generate(user.id, job_id, payload)
