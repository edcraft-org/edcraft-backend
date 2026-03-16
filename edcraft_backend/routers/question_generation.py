from uuid import UUID

from fastapi import APIRouter, status

from edcraft_backend.dependencies import CurrentUserDep, JobServiceDep
from edcraft_backend.models.job import JobType
from edcraft_backend.schemas.job import JobSubmittedResponse
from edcraft_backend.schemas.question_generation import (
    CodeAnalysisRequest,
    GenerateAssessmentFromTemplateRequest,
    GenerateQuestionFromTemplateRequest,
    GenerateTemplateRequest,
    QuestionGenerationRequest,
)

router = APIRouter(prefix="/question-generation", tags=["question-generation"])


@router.post(
    "/analyse-code",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyse_code(
    request: CodeAnalysisRequest,
    job_service: JobServiceDep,
) -> JobSubmittedResponse:
    """Submit a code analysis job. Poll GET /jobs/{job_id} for the result."""
    job = await job_service.submit(
        job_type=JobType.ANALYSE_CODE,
        params={"code": request.code},
        user_id=None,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")


@router.post(
    "/generate-question",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_question(
    request: QuestionGenerationRequest,
    job_service: JobServiceDep,
) -> JobSubmittedResponse:
    """Submit a question generation job. Poll GET /jobs/{job_id} for the result."""
    job = await job_service.submit(
        job_type=JobType.GENERATE_QUESTION,
        params=request.model_dump(),
        user_id=None,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")


@router.post(
    "/generate-template",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_template_preview(
    request: GenerateTemplateRequest,
    job_service: JobServiceDep,
) -> JobSubmittedResponse:
    """Submit a template preview generation job. Poll GET /jobs/{job_id} for the result."""
    job = await job_service.submit(
        job_type=JobType.GENERATE_TEMPLATE,
        params=request.model_dump(),
        user_id=None,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")


@router.post(
    "/from-template/{template_id}",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_question_from_template(
    user: CurrentUserDep,
    template_id: UUID,
    request: GenerateQuestionFromTemplateRequest,
    job_service: JobServiceDep,
) -> JobSubmittedResponse:
    """Submit a question-from-template job. Poll GET /jobs/{job_id} for the result."""
    job = await job_service.submit(
        job_type=JobType.QUESTION_FROM_TEMPLATE,
        params={
            "template_id": str(template_id),
            "user_id": str(user.id),
            "input_data": request.input_data,
        },
        user_id=user.id,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")


@router.post(
    "/assessment-from-template/{template_id}",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_assessment_from_template(
    user: CurrentUserDep,
    template_id: UUID,
    request: GenerateAssessmentFromTemplateRequest,
    job_service: JobServiceDep,
) -> JobSubmittedResponse:
    """Submit an assessment-from-template job. Poll GET /jobs/{job_id} for the result."""
    job = await job_service.submit(
        job_type=JobType.ASSESSMENT_FROM_TEMPLATE,
        params={
            "template_id": str(template_id),
            "user_id": str(user.id),
            "assessment_metadata": request.assessment_metadata.model_dump(),
            "question_inputs": request.question_inputs,
        },
        user_id=user.id,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")
