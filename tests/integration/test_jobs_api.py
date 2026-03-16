"""Integration tests for the Jobs API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.user import User


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetJobStatus:
    async def test_get_job_not_found(self, test_client: AsyncClient) -> None:
        """GET /jobs/{random-uuid} returns 404 when job does not exist."""
        response = await test_client.get(f"/jobs/{uuid4()}")
        assert response.status_code == 404

    async def test_get_anonymous_job_without_auth(
        self, test_client: AsyncClient
    ) -> None:
        """Anonymous jobs (no owner) can be polled by anyone with the job_id."""
        # Submit an anonymous job
        resp = await test_client.post(
            "/input-generator/generate",
            json={"inputs": {"n": {"type": "integer", "minimum": 1, "maximum": 10}}},
        )
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        # Poll without auth — should succeed
        result_resp = await test_client.get(f"/jobs/{job_id}")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"] == "completed"
        assert data["result"] is not None

    async def test_get_owned_job_wrong_user_forbidden(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Owned jobs are not accessible to a different authenticated user."""
        from tests.conftest import _create_test_client
        from tests.factories import create_and_login_user

        # Submit an owned job as `user`
        resp = await test_client.post(
            "/question-generation/from-template/00000000-0000-0000-0000-000000000001",
            json={"input_data": {"n": 5}},
        )
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        # Create a second user and try to poll the first user's job
        async with _create_test_client(db_session) as other_client:
            await create_and_login_user(other_client, db_session)
            result_resp = await other_client.get(f"/jobs/{job_id}")
            assert result_resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
class TestJobCallback:
    async def test_callback_invalid_token(self, test_client: AsyncClient) -> None:
        """POST /jobs/callback/{invalid} returns 401 for unknown token."""
        response = await test_client.post(
            "/jobs/callback/invalid-token-xyz",
            json={"result": None, "error": None},
        )
        assert response.status_code == 401

    async def test_callback_replayed_token(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A callback token can only be used once; replaying it returns 401."""
        from edcraft_backend.models.job import Job, JobStatus, JobToken
        from edcraft_backend.security import generate_token

        # Manually create a job and token in the DB
        job = Job(type="generate_inputs", status=JobStatus.RUNNING.value, user_id=None)
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)

        token = generate_token(32)
        jt = JobToken(token=token, job_id=job.id)
        db_session.add(jt)
        await db_session.flush()

        # First callback — should succeed (204)
        resp1 = await test_client.post(
            f"/jobs/callback/{token}",
            json={"result": '{"inputs": {}}', "error": None},
        )
        assert resp1.status_code == 204

        # Second callback with the same token — token is consumed, should fail (401)
        resp2 = await test_client.post(
            f"/jobs/callback/{token}",
            json={"result": '{"inputs": {}}', "error": None},
        )
        assert resp2.status_code == 401
