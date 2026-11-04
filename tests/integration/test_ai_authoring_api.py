"""End-to-end owner, review, approval, digest and generation API tests."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from edcraft_validator.application.authoring_contracts import AuthoringProgress
from httpx import ASGITransport, AsyncClient

from edcraft_backend.config.settings import (
    AuthoringProfileSettings,
    AuthoringSettings,
)
from edcraft_backend.dependencies import (
    get_ai_authoring_service,
    get_current_user,
    get_provider_connection_service,
)
from edcraft_backend.main import app
from edcraft_backend.services.ai_authoring_service import AiAuthoringService
from edcraft_backend.services.ai_authoring_store import (
    AuthoringRequestRecord,
    StoredJob,
)
from tests.ai_authoring_helpers import (
    StaticExecutor,
    make_checked_report,
    make_needs_review_report,
    run_scripted_pipeline,
)

PROFILE = AuthoringProfileSettings(
    id="test-profile",
    label="Test author",
    provider="stub",
    model="stub-model",
)


@dataclass
class FakeUser:
    id: UUID


@dataclass
class AuthoringHarness:
    client: AsyncClient
    service: AiAuthoringService
    user: FakeUser
    executor: Any


class NoConnections:
    """Connection service stub for authoring tests without a database."""

    async def list_connections(self, owner_id: UUID) -> list[Any]:
        return []


@asynccontextmanager
async def env_for(
    tmp_path: Path,
    executor: Any,
    *,
    max_queue: int = 10,
    max_quantity: int = 50,
) -> AsyncGenerator[AuthoringHarness, None]:
    settings = AuthoringSettings(
        storage_dir=tmp_path / "authoring",
        model_profiles=[PROFILE],
        max_active_jobs=1,
        max_queue=max_queue,
        max_quantity=max_quantity,
        shutdown_timeout_seconds=1.0,
    )
    service = AiAuthoringService(settings, executor=executor)
    await service.startup()
    user = FakeUser(uuid4())

    def current_user() -> FakeUser:
        return user

    def authoring_service() -> AiAuthoringService:
        return service

    app.dependency_overrides[get_ai_authoring_service] = authoring_service
    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_provider_connection_service] = NoConnections
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield AuthoringHarness(client=client, service=service, user=user, executor=executor)
    finally:
        app.dependency_overrides.clear()
        await service.wait_for_idle()
        await service.shutdown(0.5)


@pytest_asyncio.fixture
async def checked_env(tmp_path: Path) -> AsyncGenerator[AuthoringHarness, None]:
    async with env_for(
        tmp_path, StaticExecutor(lambda command: make_checked_report(command))
    ) as env:
        yield env


def payload(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "domain": "code",
        "prompt": "Create an arithmetic tracing question",
        "difficulty": "easy",
        "num_distractors": 3,
        "model_profile": "test-profile",
    }
    value.update(overrides)
    return value


async def submit(env: AuthoringHarness, **overrides: Any) -> UUID:
    response = await env.client.post("/ai-authoring/jobs", json=payload(**overrides))
    assert response.status_code == 202, response.text
    return UUID(response.json()["job_id"])


async def complete_job(env: AuthoringHarness, **overrides: Any) -> UUID:
    job_id = await submit(env, **overrides)
    await env.service.wait_for_idle()
    response = await env.client.get(f"/ai-authoring/jobs/{job_id}")
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "completed", response.text
    return job_id


async def review(env: AuthoringHarness, job_id: UUID) -> dict[str, Any]:
    response = await env.client.get(f"/ai-authoring/jobs/{job_id}/review")
    assert response.status_code == 200, response.text
    return response.json()


async def approve(env: AuthoringHarness, job_id: UUID, digest: str) -> Any:
    return await env.client.post(
        f"/ai-authoring/jobs/{job_id}/approval",
        json={"artifact_sha256": digest, "decision": "approved"},
    )


@pytest.mark.asyncio
async def test_all_authoring_endpoints_require_sign_in(
    checked_env: AuthoringHarness,
) -> None:
    app.dependency_overrides.pop(get_current_user, None)
    response = await checked_env.client.get("/ai-authoring/capabilities")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_capabilities_are_safe_and_server_configured(checked_env: AuthoringHarness) -> None:
    response = await checked_env.client.get("/ai-authoring/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled_domains"] == ["code"]
    assert body["difficulty_labels"] == ["easy", "medium", "hard"]
    assert body["model_profiles"] == [
        {
            "id": "test-profile",
            "label": "Test author",
            "provider": "stub",
            "model": "stub-model",
        }
    ]
    assert body["max_quantity"] == 50
    assert body["min_distractors"] == 1
    assert body["max_distractors"] == 10
    assert body["default_distractors"] == 3
    assert body["judge"]["provider"]
    assert body["judge"]["model"]
    assert "api_key" not in response.text
    assert "http" not in response.text


@pytest.mark.asyncio
async def test_review_preview_approval_and_generation_flow(checked_env: AuthoringHarness) -> None:
    env = checked_env
    job_id = await complete_job(env)
    status = (await env.client.get(f"/ai-authoring/jobs/{job_id}")).json()
    assert status["result"]["status"] == "checked"
    assert status["approval"] is None

    envelope = await review(env, job_id)
    digest = envelope["artifact_sha256"]
    assert envelope["artifact_id"] == status["result"]["artifact_id"]
    assert envelope["request"]["prompt"] == payload()["prompt"]
    assert envelope["template"]["candidate"]["code"].startswith("def calculate")
    assert envelope["template"]["candidate"]["question_template"]
    assert envelope["template"]["candidate"]["distractors"]
    assert envelope["template"]["template_id"] == "arithmetic.linear_sum"
    assert envelope["candidate_is_historical_attempt"] is True
    assert envelope["candidate"]["code"] == envelope["template"]["candidate"]["code"]
    assert envelope["fixed_plan"] == ["code_validate_answers_and_distractors"]
    assert envelope["validation_limits"]["examples_checked"] == 4
    assert envelope["attempts"][0]["checks"][0]["status"] == "passed"
    assert "never-return-this" not in str(envelope)
    assert "raw exception text" not in str(envelope)
    assert "provider_settings" not in str(envelope)
    assert "api_key" not in str(envelope)

    preview = await env.client.post(f"/ai-authoring/jobs/{job_id}/preview", json={"seed": 7})
    again = await env.client.post(f"/ai-authoring/jobs/{job_id}/preview", json={"seed": 7})
    assert preview.status_code == 200, preview.text
    assert preview.json() == again.json()
    assert preview.json()["question"]["question"]["code"].startswith("def calculate")
    assert preview.json()["question"]["seed"] == 7
    assert preview.json()["artifact_sha256"] == digest
    assert env.executor.calls == 1

    unapproved = await env.client.post(
        f"/ai-authoring/jobs/{job_id}/generate",
        json={"artifact_sha256": digest, "seed": 5, "quantity": 2},
    )
    assert unapproved.status_code == 409

    stale = await approve(env, job_id, "0" * 64)
    assert stale.status_code == 409

    approved = await approve(env, job_id, digest)
    assert approved.status_code == 200, approved.text
    assert approved.json()["decision"] == "approved"

    generated = await env.client.post(
        f"/ai-authoring/jobs/{job_id}/generate",
        json={"artifact_sha256": digest, "seed": 5, "quantity": 3},
    )
    assert generated.status_code == 200, generated.text
    batch = generated.json()
    assert batch["requested_quantity"] == 3
    assert batch["actual_quantity"] == 3
    assert [question["seed"] for question in batch["questions"]] == [5, 6, 7]
    assert batch["duplicates"] == batch["actual_quantity"] - batch["distinct_count"]
    assert batch["artifact_sha256"] == digest

    repeated = await env.client.post(
        f"/ai-authoring/jobs/{job_id}/generate",
        json={"artifact_sha256": digest, "seed": 5, "quantity": 3},
    )
    assert repeated.json() == batch
    stored = (await env.client.get(f"/ai-authoring/jobs/{job_id}")).json()
    assert stored["last_generation"]["base_seed"] == 5
    assert stored["last_generation"]["requested_quantity"] == 3
    assert stored["last_generation"]["artifact_sha256"] == digest

    rejected = await env.client.post(
        f"/ai-authoring/jobs/{job_id}/approval",
        json={"artifact_sha256": digest, "decision": "rejected"},
    )
    assert rejected.status_code == 200
    blocked = await env.client.post(
        f"/ai-authoring/jobs/{job_id}/generate",
        json={"artifact_sha256": digest, "seed": 5, "quantity": 1},
    )
    assert blocked.status_code == 409

    reapproved = await approve(env, job_id, digest)
    assert reapproved.status_code == 200
    assert env.executor.calls == 1

    listed = await env.client.get("/ai-authoring/jobs")
    assert listed.status_code == 200
    assert [item["job_id"] for item in listed.json()] == [str(job_id)]

    env.user.id = uuid4()
    assert (await env.client.get(f"/ai-authoring/jobs/{job_id}")).status_code == 404
    assert (await env.client.get("/ai-authoring/jobs")).json() == []


@pytest.mark.asyncio
async def test_real_scripted_library_pipeline_round_trips_through_api(
    tmp_path: Path,
) -> None:
    async with env_for(tmp_path, run_scripted_pipeline) as env:
        job_id = await complete_job(env)
        envelope = await review(env, job_id)
        assert envelope["template"]["candidate"]["code"].startswith("def calculate")
        assert envelope["checks"][0]["status"] == "passed"
        assert envelope["validation_limits"]["examples_checked"] > 0

        digest = envelope["artifact_sha256"]
        assert (await approve(env, job_id, digest)).status_code == 200
        preview = await env.client.post(f"/ai-authoring/jobs/{job_id}/preview", json={"seed": 3})
        assert preview.status_code == 200, preview.text
        assert preview.json()["question"]["template_id"] == envelope["template"]["template_id"]
        batch = await env.client.post(
            f"/ai-authoring/jobs/{job_id}/generate",
            json={"artifact_sha256": digest, "seed": 3, "quantity": 2},
        )
        assert batch.status_code == 200, batch.text
        assert [item["seed"] for item in batch.json()["questions"]] == [3, 4]


@pytest.mark.asyncio
async def test_advisory_mismatch_is_visible_but_never_blocks(
    tmp_path: Path,
) -> None:
    async with env_for(
        tmp_path,
        StaticExecutor(lambda command: make_checked_report(command, advisory_failure=True)),
    ) as env:
        job_id = await complete_job(env)
        envelope = await review(env, job_id)
        assert envelope["difficulty"]["decision"] == "advisory_mismatch"
        advisory = [check for check in envelope["checks"] if check["advisory"]]
        technical = [check for check in envelope["checks"] if not check["advisory"]]
        assert advisory and advisory[0]["status"] == "failed"
        assert technical and technical[0]["status"] == "passed"
        approved = await approve(env, job_id, envelope["artifact_sha256"])
        assert approved.status_code == 200
        generated = await env.client.post(
            f"/ai-authoring/jobs/{job_id}/generate",
            json={
                "artifact_sha256": envelope["artifact_sha256"],
                "seed": 0,
                "quantity": 2,
            },
        )
        assert generated.status_code == 200


@pytest.mark.asyncio
async def test_generate_enforces_configured_max_quantity(tmp_path: Path) -> None:
    async with env_for(
        tmp_path,
        StaticExecutor(lambda command: make_checked_report(command)),
        max_quantity=2,
    ) as env:
        job_id = await complete_job(env)
        envelope = await review(env, job_id)
        digest = envelope["artifact_sha256"]
        assert (await approve(env, job_id, digest)).status_code == 200

        too_many = await env.client.post(
            f"/ai-authoring/jobs/{job_id}/generate",
            json={"artifact_sha256": digest, "seed": 0, "quantity": 3},
        )
        assert too_many.status_code == 422
        allowed = await env.client.post(
            f"/ai-authoring/jobs/{job_id}/generate",
            json={"artifact_sha256": digest, "seed": 0, "quantity": 2},
        )
        assert allowed.status_code == 200
        assert allowed.json()["actual_quantity"] == 2


@pytest.mark.asyncio
async def test_technical_failure_has_no_usable_artifact(tmp_path: Path) -> None:
    async with env_for(
        tmp_path, StaticExecutor(lambda command: make_needs_review_report(command))
    ) as env:
        job_id = await complete_job(env)
        status = (await env.client.get(f"/ai-authoring/jobs/{job_id}")).json()
        assert status["result"]["status"] == "needs_review"
        envelope = await review(env, job_id)
        assert envelope["artifact_id"] is None
        assert envelope["artifact_sha256"] is None
        assert envelope["template"] is None
        assert any(check["status"] == "failed" for check in envelope["checks"])
        assert (await approve(env, job_id, "0" * 64)).status_code == 409
        assert (
            await env.client.post(f"/ai-authoring/jobs/{job_id}/preview", json={"seed": 0})
        ).status_code == 409
        assert (
            await env.client.post(
                f"/ai-authoring/jobs/{job_id}/generate",
                json={"artifact_sha256": "0" * 64, "seed": 0, "quantity": 1},
            )
        ).status_code == 409


@pytest.mark.asyncio
async def test_advisory_unavailable_is_visible_but_never_blocks(
    tmp_path: Path,
) -> None:
    async with env_for(
        tmp_path,
        StaticExecutor(lambda command: make_checked_report(command, advisory_unavailable=True)),
    ) as env:
        job_id = await complete_job(env)
        envelope = await review(env, job_id)
        advisory = [check for check in envelope["checks"] if check["advisory"]]
        assert advisory and advisory[0]["status"] == "error"
        assert advisory[0]["error"] == "Check did not complete."
        assert "ADVISORY_ASSESSMENT_UNAVAILABLE" in envelope["warnings"]
        assert "raw advisory transport failure" not in str(envelope)
        assert (await approve(env, job_id, envelope["artifact_sha256"])).status_code == 200
        generated = await env.client.post(
            f"/ai-authoring/jobs/{job_id}/generate",
            json={
                "artifact_sha256": envelope["artifact_sha256"],
                "seed": 0,
                "quantity": 1,
            },
        )
        assert generated.status_code == 200


@pytest.mark.asyncio
async def test_checked_status_with_failed_technical_evidence_is_not_usable(
    tmp_path: Path,
) -> None:
    async with env_for(
        tmp_path,
        StaticExecutor(lambda command: make_checked_report(command, technical_failure=True)),
    ) as env:
        job_id = await complete_job(env)
        envelope = await review(env, job_id)
        assert envelope["artifact_sha256"]
        assert any(
            check["status"] == "failed" and not check["advisory"] for check in envelope["checks"]
        )
        digest = envelope["artifact_sha256"]
        assert (await approve(env, job_id, digest)).status_code == 409
        assert (
            await env.client.post(f"/ai-authoring/jobs/{job_id}/preview", json={"seed": 0})
        ).status_code == 409
        assert (
            await env.client.post(
                f"/ai-authoring/jobs/{job_id}/generate",
                json={"artifact_sha256": digest, "seed": 0, "quantity": 1},
            )
        ).status_code == 409


@pytest.mark.asyncio
async def test_tampered_artifact_is_rejected_everywhere(checked_env: AuthoringHarness) -> None:
    env = checked_env
    job_id = await complete_job(env)
    envelope = await review(env, job_id)
    artifact_path = env.service.store.root / "artifacts" / str(job_id) / "artifact.json"
    artifact_path.write_bytes(b'{"tampered":true}')

    assert (await env.client.get(f"/ai-authoring/jobs/{job_id}/review")).status_code == 409
    assert (
        await env.client.post(f"/ai-authoring/jobs/{job_id}/preview", json={"seed": 0})
    ).status_code == 409
    assert (await approve(env, job_id, envelope["artifact_sha256"])).status_code == 409
    assert (
        await env.client.post(
            f"/ai-authoring/jobs/{job_id}/generate",
            json={
                "artifact_sha256": envelope["artifact_sha256"],
                "seed": 0,
                "quantity": 1,
            },
        )
    ).status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("damage", ["missing", "invalid"])
async def test_damaged_review_report_fails_closed_everywhere(
    checked_env: AuthoringHarness, damage: str
) -> None:
    env = checked_env
    job_id = await complete_job(env)
    envelope = await review(env, job_id)
    digest = envelope["artifact_sha256"]
    assert (await approve(env, job_id, digest)).status_code == 200

    report_path = env.service.store.root / "artifacts" / str(job_id) / "report.json"
    if damage == "missing":
        report_path.unlink()
    else:
        report_path.write_bytes(b"not a valid authoring report")

    assert (await env.client.get(f"/ai-authoring/jobs/{job_id}/review")).status_code == 409
    assert (await approve(env, job_id, digest)).status_code == 409
    assert (
        await env.client.post(f"/ai-authoring/jobs/{job_id}/preview", json={"seed": 0})
    ).status_code == 409
    assert (
        await env.client.post(
            f"/ai-authoring/jobs/{job_id}/generate",
            json={"artifact_sha256": digest, "seed": 0, "quantity": 1},
        )
    ).status_code == 409

    stored = (await env.client.get(f"/ai-authoring/jobs/{job_id}")).json()
    assert stored["last_generation"] is None
    assert stored["approval"]["decision"] == "approved"


@pytest.mark.asyncio
async def test_generation_rechecks_revoked_approval_under_store_lock(
    checked_env: AuthoringHarness,
) -> None:
    env = checked_env
    job_id = await complete_job(env)
    envelope = await review(env, job_id)
    digest = envelope["artifact_sha256"]
    assert (await approve(env, job_id, digest)).status_code == 200

    original_read_artifact = env.service.store.read_artifact
    entered = threading.Event()
    release = threading.Event()

    def gated_read_artifact(target_job_id: UUID) -> bytes:
        if not entered.is_set():
            entered.set()
            if not release.wait(5):
                raise RuntimeError("test generate gate timed out")
        return original_read_artifact(target_job_id)

    env.service.store.read_artifact = gated_read_artifact  # type: ignore[assignment]
    try:
        generating = asyncio.create_task(
            env.client.post(
                f"/ai-authoring/jobs/{job_id}/generate",
                json={"artifact_sha256": digest, "seed": 0, "quantity": 1},
            )
        )
        assert await asyncio.to_thread(entered.wait, 2)
        rejected = await env.client.post(
            f"/ai-authoring/jobs/{job_id}/approval",
            json={"artifact_sha256": digest, "decision": "rejected"},
        )
        assert rejected.status_code == 200, rejected.text
        release.set()
        generated = await generating
        assert generated.status_code == 409, generated.text
    finally:
        release.set()

    stored = (await env.client.get(f"/ai-authoring/jobs/{job_id}")).json()
    assert stored["last_generation"] is None
    assert stored["approval"]["decision"] == "rejected"


@pytest.mark.asyncio
async def test_non_default_distractor_count_is_accepted_and_stored(
    checked_env: AuthoringHarness,
) -> None:
    response = await checked_env.client.post(
        "/ai-authoring/jobs", json=payload(num_distractors=7)
    )
    assert response.status_code == 202, response.text

    job_id = UUID(response.json()["job_id"])
    stored = checked_env.service.store.get_job(job_id)
    assert stored.request.num_distractors == 7


@pytest.mark.asyncio
async def test_strict_input_bounds_and_unknown_profile(checked_env: AuthoringHarness) -> None:
    env = checked_env
    for bad_payload in (
        payload(prompt=""),
        payload(prompt="   "),
        payload(num_distractors=0),
        payload(num_distractors=11),
        payload(num_distractors=True),
        payload(domain="math"),
        payload(model_profile="missing"),
    ):
        response = await env.client.post("/ai-authoring/jobs", json=bad_payload)
        assert response.status_code == 422, (bad_payload, response.text)

    job_id = await complete_job(env)
    envelope = await review(env, job_id)
    digest = envelope["artifact_sha256"]
    await approve(env, job_id, digest)

    for body in (
        {"artifact_sha256": digest, "seed": 0, "quantity": 0},
        {"artifact_sha256": digest, "seed": 0, "quantity": 51},
        {"artifact_sha256": digest, "seed": -1, "quantity": 1},
        {"artifact_sha256": digest, "seed": 1.5, "quantity": 1},
        {"artifact_sha256": digest, "seed": True, "quantity": 1},
        {"artifact_sha256": digest, "seed": 2_147_483_647, "quantity": 2},
        {"artifact_sha256": "not-a-digest", "seed": 0, "quantity": 1},
    ):
        response = await env.client.post(f"/ai-authoring/jobs/{job_id}/generate", json=body)
        assert response.status_code == 422, (body, response.text)

    for seed in (-1, True, 1.5):
        response = await env.client.post(
            f"/ai-authoring/jobs/{job_id}/preview", json={"seed": seed}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_admission_is_bounded_and_progress_is_running_only(
    tmp_path: Path,
) -> None:
    release = threading.Event()
    started = threading.Event()

    class BlockingExecutor(StaticExecutor):
        def __call__(self, command: Any, plan: Any, on_progress: Any = None) -> Any:
            on_progress(AuthoringProgress(phase="generating", attempt=1))
            started.set()
            if not release.wait(5):
                raise RuntimeError("test executor timed out")
            return super().__call__(command, plan, on_progress)

    async with env_for(
        tmp_path,
        BlockingExecutor(lambda command: make_checked_report(command)),
        max_queue=1,
    ) as env:
        first = await submit(env)
        assert await asyncio.to_thread(started.wait, 2)
        running = (await env.client.get(f"/ai-authoring/jobs/{first}")).json()
        assert running["state"] == "running"
        assert running["progress"] == {"phase": "generating", "attempt": 1}

        second = await submit(env)
        assert (await env.client.get(f"/ai-authoring/jobs/{second}")).json()["state"] == "queued"
        third = await env.client.post("/ai-authoring/jobs", json=payload())
        assert third.status_code == 429

        release.set()
        await env.service.wait_for_idle()
        assert (await env.client.get(f"/ai-authoring/jobs/{first}")).json()["state"] == "completed"
        assert (await env.client.get(f"/ai-authoring/jobs/{second}")).json()["state"] == "completed"


@pytest.mark.asyncio
async def test_restart_reconciles_only_unfinished_jobs(checked_env: AuthoringHarness) -> None:
    env = checked_env
    job_id = await complete_job(env)
    envelope = await review(env, job_id)
    assert (await approve(env, job_id, envelope["artifact_sha256"])).status_code == 200

    now = datetime.now(UTC)
    interrupted_id = uuid4()
    store = env.service.store
    store.create_job(
        StoredJob(
            job_id=interrupted_id,
            owner_id=env.user.id,
            request=AuthoringRequestRecord(
                prompt="Interrupted job",
                difficulty="easy",
                num_distractors=3,
                model_profile="test-profile",
            ),
            provider="stub",
            model="stub-model",
            library_revision="test-revision",
            created_at=now,
            updated_at=now,
        )
    )
    store.mark_started(interrupted_id)

    await env.service.startup()

    interrupted = (await env.client.get(f"/ai-authoring/jobs/{interrupted_id}")).json()
    assert interrupted["state"] == "failed"
    assert interrupted["result"] is None
    assert interrupted["error"]["code"] == "SERVER_RESTARTED"
    assert "restart" in interrupted["error"]["message"].lower()

    completed = (await env.client.get(f"/ai-authoring/jobs/{job_id}")).json()
    assert completed["state"] == "completed"
    assert completed["approval"]["decision"] == "approved"
    assert completed["result"]["artifact_id"] == envelope["artifact_id"]
    assert completed["approval"]["artifact_sha256"] == envelope["artifact_sha256"]
