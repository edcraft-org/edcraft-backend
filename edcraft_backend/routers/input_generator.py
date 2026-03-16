"""Input generator endpoints."""

from fastapi import APIRouter, status

from edcraft_backend.dependencies import JobServiceDep
from edcraft_backend.models.job import JobType
from edcraft_backend.schemas.input_generator import GenerateInputsRequest
from edcraft_backend.schemas.job import JobSubmittedResponse

router = APIRouter(prefix="/input-generator", tags=["input-generator"])


@router.post(
    "/generate",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_inputs(
    request: GenerateInputsRequest,
    job_service: JobServiceDep,
) -> JobSubmittedResponse:
    """Submit an input generation job. Poll GET /jobs/{job_id} for the result."""
    job = await job_service.submit(
        job_type=JobType.GENERATE_INPUTS,
        params={"inputs": request.inputs},
        user_id=None,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")
