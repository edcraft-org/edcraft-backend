"""Service for submitting and managing async Nomad jobs."""

from uuid import UUID

from edcraft_backend.config import settings
from edcraft_backend.exceptions import (
    InvalidTokenError,
    ResourceNotFoundError,
    UnauthorizedAccessError,
)
from edcraft_backend.executors.nomad import NomadExecutor
from edcraft_backend.models.job import Job, JobStatus, JobType
from edcraft_backend.repositories.job_repository import JobRepository, JobTokenRepository
from edcraft_backend.security import generate_token


class JobService:
    """Orchestrates job submission, callback handling, and status retrieval."""

    def __init__(
        self,
        job_repo: JobRepository,
        job_token_repo: JobTokenRepository,
        executor: NomadExecutor | None,
    ) -> None:
        self.job_repo = job_repo
        self.job_token_repo = job_token_repo
        self.executor = executor

    async def submit(
        self,
        job_type: JobType,
        params: dict[str, object],
        user_id: UUID | None = None,
    ) -> Job:
        """Create a Job record, issue a callback token, and submit to Nomad."""
        job = Job(type=job_type.value, status=JobStatus.QUEUED.value, user_id=user_id)
        job = await self.job_repo.create(job)

        token = generate_token(32)
        await self.job_token_repo.create(token=token, job_id=job.id)

        callback_url = f"{settings.nomad.callback_base_url}/jobs/callback/{token}"
        nomad_job_id = f"edcraft-{job_type.value.replace('_', '-')}-{job.id}"

        if self.executor is None:
            raise RuntimeError("No executor configured")
        try:
            await self.executor.submit_job(
                nomad_job_id=nomad_job_id,
                job_type=job_type.value,
                params=params,
                callback_url=callback_url,
            )
            await self.job_repo.update_status(
                job.id, JobStatus.RUNNING.value, nomad_job_id=nomad_job_id
            )
        except Exception:
            await self.job_repo.update_status(job.id, JobStatus.FAILED.value)
            raise

        return job

    async def on_callback(
        self,
        token: str,
        result_json: str | None,
        error: str | None,
    ) -> None:
        """Validate the one-time token and persist the job result.

        Called by the Nomad worker via POST /jobs/callback/{token}.
        """
        job_token = await self.job_token_repo.get_valid_by_token(token)
        if job_token is None:
            raise InvalidTokenError("Invalid or already consumed callback token")

        await self.job_token_repo.consume(token)
        await self.job_repo.complete(
            job_id=job_token.job_id,
            result_json=result_json,
            error=error,
        )

    async def get_job(self, job_id: UUID, user_id: UUID | None = None) -> Job:
        """Fetch a job, enforcing ownership for jobs that have an owner.

        Anonymous jobs (user_id=None) are accessible to anyone with the job_id.
        Owned jobs are restricted to the owning user.
        """
        job = await self.job_repo.get_by_id(job_id)
        if job is None:
            raise ResourceNotFoundError("Job", str(job_id))
        if job.user_id is not None and job.user_id != user_id:
            raise UnauthorizedAccessError("Job", str(job_id))
        return job
