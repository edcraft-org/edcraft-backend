"""Jobs router: poll job status and accept worker callbacks."""

import json
from uuid import UUID

from fastapi import APIRouter, status

from edcraft_backend.dependencies import CurrentUserOptionalDep, JobServiceDep
from edcraft_backend.schemas.job import JobCallbackPayload, JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    user: CurrentUserOptionalDep,
    job_service: JobServiceDep,
) -> JobStatusResponse:
    """Poll the status and result of an async job.

    Anonymous jobs (submitted without authentication) can be polled by anyone
    who knows the job_id. Owned jobs are restricted to the owning user.
    """
    user_id = user.id if user else None
    job = await job_service.get_job(job_id, user_id)
    result = json.loads(job.result_json) if job.result_json else None
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        result=result,
        error=job.error_message,
    )


@router.post(
    "/callback/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def job_callback(
    token: str,
    payload: JobCallbackPayload,
    job_service: JobServiceDep,
) -> None:
    """Receive results from a Nomad worker.

    The one-time token in the URL authenticates the request.
    """
    await job_service.on_callback(
        token=token,
        result_json=payload.result,
        error=payload.error,
    )
