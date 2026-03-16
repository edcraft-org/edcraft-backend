"""Repositories for Job and JobToken models."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from edcraft_backend.models.job import Job, JobStatus, JobToken


class JobRepository:
    """Data access for Job records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, job: Job) -> Job:
        """Persist a new Job and return it with server-generated fields populated."""
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: UUID) -> Job | None:
        """Fetch a Job by primary key."""
        stmt = select(Job).where(Job.id == job_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        job_id: UUID,
        status: str,
        nomad_job_id: str | None = None,
    ) -> None:
        """Update job status."""
        values: dict[str, object] = {"status": status}
        if nomad_job_id is not None:
            values["nomad_job_id"] = nomad_job_id
        stmt = update(Job).where(Job.id == job_id).values(**values)
        await self.db.execute(stmt)
        await self.db.flush()

    async def complete(
        self,
        job_id: UUID,
        result_json: str | None,
        error: str | None,
    ) -> None:
        """Mark a job as completed or failed and store the result/error."""
        status = JobStatus.FAILED.value if error else JobStatus.COMPLETED.value
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=status,
                result_json=result_json,
                error_message=error,
                completed_at=func.now(),
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()


class JobTokenRepository:
    """Data access for JobToken records (one-time callback tokens)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, token: str, job_id: UUID) -> JobToken:
        """Create a new one-time token for the given job."""
        jt = JobToken(token=token, job_id=job_id)
        self.db.add(jt)
        await self.db.flush()
        return jt

    async def get_valid_by_token(self, token: str) -> JobToken | None:
        """Return the token only if it exists, has not been consumed, and is not revoked."""
        stmt = select(JobToken).where(
            JobToken.token == token,
            JobToken.revoked.is_(False),
            JobToken.consumed_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def consume(self, token: str) -> None:
        """Mark the token as consumed so it cannot be used again."""
        stmt = (
            update(JobToken)
            .where(JobToken.token == token)
            .values(consumed_at=func.now())
        )
        await self.db.execute(stmt)
        await self.db.flush()
