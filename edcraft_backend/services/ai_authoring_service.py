"""Business rules for owner-scoped AI authoring, review and generation."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from edcraft_validator.application.authoring_api import (
    AuthoringJobCommand,
    PublicAuthoringError,
)
from edcraft_validator.application.authoring_contracts import (
    AuthoringResult,
    GenerationAttempt,
)
from edcraft_validator.application.template_workflow import TemplateApplication
from edcraft_validator.domains.code.code_schemas import (
    CodeQuestionInstance,
    CodeTemplateCandidate,
    TemplateValidationSummary,
    ValidatedCodeTemplate,
)
from edcraft_validator.domains.code.code_types import (
    DEFAULT_DISTRACTORS,
    MAX_DISTRACTORS,
    MIN_DISTRACTORS,
)
from edcraft_validator.domains.domain_registry import create_domain
from edcraft_validator.llm.judge_configuration import load_judge_settings
from edcraft_validator.llm.llm_contracts import TemplateProviderSelection
from pydantic import ValidationError

from edcraft_backend.config.settings import AuthoringProfileSettings, AuthoringSettings
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.schemas.ai_authoring import (
    ApprovalRequest,
    ApprovalResponse,
    AuthoringCapabilitiesResponse,
    AuthoringJobStatusResponse,
    AuthoringJobSummary,
    AuthoringModelProfile,
    AuthoringModelSelection,
    AuthoringRequestView,
    AuthoringReviewResponse,
    GeneratedQuestionsBatch,
    GenerateRequest,
    GenerationMetadata,
    JudgeDisplay,
    PreviewResponse,
    ReviewAttempt,
    ReviewCheck,
    ReviewFinding,
    ReviewTemplate,
    StoredReviewerApproval,
    SubmitAuthoringJobRequest,
    ValidationLimits,
)
from edcraft_backend.schemas.provider_connection import ProviderConnectionResponse
from edcraft_backend.services.ai_authoring_providers import (
    JobCredentials,
    JobModelPlan,
    ModelPlan,
    ProviderCredentials,
)
from edcraft_backend.services.ai_authoring_runner import AuthoringRunner, JobExecutor
from edcraft_backend.services.ai_authoring_store import (
    ApprovalRecord,
    AuthoringConflict,
    AuthoringNotFound,
    AuthoringRequestRecord,
    AuthoringStorageUnavailable,
    AuthoringStore,
    StoredJob,
    require_bound_report,
    require_reusable_evidence,
)

ApprovalView = StoredReviewerApproval

logger = logging.getLogger(__name__)

# Must match [tool.uv.sources].edcraft-validator.rev in pyproject.toml.
LIBRARY_REVISION = "e90eced9b9c51792ab4afa821ffbd46c9aba4917"
MAX_FINDING_TEXT = 2_000


class AuthoringValidationError(EdCraftBaseException):
    """A safe request/config selection error (HTTP 422)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 422)


class AiAuthoringService:
    """Thin integration layer over the pinned AI library and file store."""

    def __init__(
        self,
        settings: AuthoringSettings,
        *,
        store: AuthoringStore | None = None,
        executor: JobExecutor | None = None,
    ) -> None:
        self.settings = settings
        self.store = store or AuthoringStore(settings)
        self.runner = AuthoringRunner(self.store, settings, executor)

    async def startup(self) -> None:
        """Prepare durable storage, reconcile interruptions and bind the runner."""
        await asyncio.to_thread(self.store.ensure_ready)
        await asyncio.to_thread(self.store.reconcile_startup)
        await self.runner.start()

    async def shutdown(self, timeout: float | None = None) -> None:
        """Allow admitted work a bounded chance to finish before process exit."""
        await self.runner.shutdown(
            self.settings.shutdown_timeout_seconds if timeout is None else timeout
        )

    async def capabilities(
        self, connections: list[ProviderConnectionResponse] | None = None
    ) -> AuthoringCapabilitiesResponse:
        """Return safe server profiles plus the caller's own connections."""
        profiles = [
            AuthoringModelProfile(
                id=profile.id,
                label=profile.label,
                provider=profile.provider,
                model=profile.model,
            )
            for profile in self.settings.model_profiles
        ]
        judge: JudgeDisplay | None
        try:
            configured = load_judge_settings()
            judge = JudgeDisplay(
                label=f"{configured.provider} · {configured.model}",
                provider=configured.provider,
                model=configured.model,
            )
        except (ValueError, ValidationError):
            logger.warning("Configured advisory judge settings are invalid")
            judge = None
        return AuthoringCapabilitiesResponse(
            enabled_domains=["code"],
            difficulty_labels=["easy", "medium", "hard"],
            model_profiles=profiles,
            # Disabled connections stay visible in settings but cannot write questions.
            connections=[item for item in (connections or []) if item.enabled],
            judge=judge,
            max_quantity=min(self.settings.max_quantity, 50),
            min_distractors=MIN_DISTRACTORS,
            max_distractors=MAX_DISTRACTORS,
            default_distractors=DEFAULT_DISTRACTORS,
        )

    async def submit(
        self,
        owner_id: UUID,
        request: SubmitAuthoringJobRequest,
        credentials: JobCredentials | None = None,
    ) -> StoredJob:
        """Admit and persist one queued authoring job."""
        resolved = credentials or JobCredentials()
        if request.connection_id is not None:
            if resolved.author is None:
                raise AuthoringValidationError("Model connection is unavailable.")
            author = resolved.author
            author_plan = ModelPlan(
                selection=TemplateProviderSelection(
                    provider=author.provider, model=author.model
                ),
                credentials=author,
            )
            provider = author.provider
            model = author.model
            profile_id = None
            connection_id = request.connection_id
        else:
            if request.model_profile is None:
                raise AuthoringValidationError("Choose a question-writing model.")
            profile = self._profile(request.model_profile)
            author_plan = ModelPlan(
                selection=TemplateProviderSelection(
                    provider=profile.provider, model=profile.model
                )
            )
            provider = profile.provider
            model = profile.model
            profile_id = profile.id
            connection_id = None

        difficulty_plan = self._judge_model_plan(
            request.judges.difficulty if request.judges else None,
            default=author_plan,
            credentials=resolved.difficulty,
            label="Difficulty",
        )
        relevance_plan = self._judge_model_plan(
            request.judges.relevance if request.judges else None,
            default=author_plan,
            credentials=resolved.relevance,
            label="Relevance",
        )
        plan = JobModelPlan(
            author=author_plan,
            difficulty=difficulty_plan,
            relevance=relevance_plan,
        )

        await self.runner.reserve(owner_id)
        job_id = uuid4()
        now = _now()
        command = AuthoringJobCommand(
            job_id=job_id,
            domain="code",
            author=author_plan.selection,
            request={
                "prompt": request.prompt,
                "difficulty": request.difficulty,
                "num_distractors": request.num_distractors,
            },
        )
        job = StoredJob(
            job_id=job_id,
            owner_id=owner_id,
            request=AuthoringRequestRecord(
                prompt=request.prompt,
                difficulty=request.difficulty,
                num_distractors=request.num_distractors,
                domain="code",
                model_profile=profile_id,
                connection_id=connection_id,
                model=model,
                judges=request.judges,
            ),
            provider=provider,
            model=model,
            connection_id=connection_id,
            library_revision=LIBRARY_REVISION,
            state="queued",
            created_at=now,
            updated_at=now,
        )
        persistence = asyncio.create_task(asyncio.to_thread(self.store.create_job, job))
        try:
            await asyncio.shield(persistence)
        except asyncio.CancelledError:
            # The write cannot be interrupted, so keep the job and give it
            # a worker before propagating cancellation to the caller.
            await self._finish_cancelled_submission(persistence, job, command, plan, owner_id)
            raise
        except Exception:
            await self.runner.release(owner_id)
            raise
        try:
            self.runner.start_job(job_id, command, plan, owner_id)
        except Exception:
            await self._fail_scheduled_job(job_id, owner_id)
            raise
        return job

    async def _finish_cancelled_submission(
        self,
        persistence: asyncio.Task[StoredJob],
        job: StoredJob,
        command: AuthoringJobCommand,
        plan: JobModelPlan,
        owner_id: UUID,
    ) -> None:
        """Let persistence finish, then schedule the job so it is not orphaned."""
        try:
            await persistence
        except Exception:
            await self.runner.release(owner_id)
            return
        try:
            self.runner.start_job(job.job_id, command, plan, owner_id)
        except Exception:
            await self._fail_scheduled_job(job.job_id, owner_id)

    async def _fail_scheduled_job(self, job_id: UUID, owner_id: UUID) -> None:
        """Fail a persisted job that could not be scheduled and release its slot."""
        try:
            await asyncio.to_thread(
                self.store.fail_job,
                job_id,
                PublicAuthoringError(
                    code="AUTHORING_FAILED",
                    message="Authoring could not be scheduled.",
                ),
            )
        finally:
            await self.runner.release(owner_id)

    async def list_jobs(self, owner_id: UUID) -> list[StoredJob]:
        return await asyncio.to_thread(self.store.list_jobs, owner_id)

    async def get_job(self, owner_id: UUID, job_id: UUID) -> StoredJob:
        return await asyncio.to_thread(self.store.get_owned_job, job_id, owner_id)

    async def wait_for_idle(self) -> None:
        """Expose deterministic completion to focused tests."""
        await self.runner.wait_for_idle()

    async def review(self, owner_id: UUID, job_id: UUID) -> AuthoringReviewResponse:
        """Return sanitized evidence sufficient for an educator decision."""
        job = await self.get_job(owner_id, job_id)
        report: AuthoringResult | None = None
        if job.state in {"completed", "failed"}:
            try:
                report = await asyncio.to_thread(self.store.read_report, job_id)
            except AuthoringConflict:
                if job.artifact_sha256 is not None or job.artifact_id is not None:
                    raise
                report = None

        artifact: ValidatedCodeTemplate | None = None
        if job.artifact_sha256 and job.artifact_id:
            _, artifact = await self._verified_artifact(job)
            require_bound_report(
                job,
                expected_artifact_sha256=job.artifact_sha256,
                report=report,
            )

        attempts = [
            self._project_attempt(attempt) for attempt in (report.attempts if report else [])
        ]
        checks = attempts[-1].checks if attempts else []
        candidate = attempts[-1].candidate if attempts else None
        limits = self._limits(artifact.validation) if artifact is not None else None
        summary = job.result
        return AuthoringReviewResponse(
            job_id=job.job_id,
            state=job.state,
            artifact_id=job.artifact_id,
            artifact_sha256=job.artifact_sha256,
            library_revision=job.library_revision,
            request=AuthoringRequestView.model_validate(job.request.model_dump()),
            template=(
                ReviewTemplate(
                    template_id=artifact.template.template_id,
                    candidate=artifact.template,
                )
                if artifact is not None
                else None
            ),
            checks=checks,
            attempts=attempts,
            fixed_plan=list(report.fixed_plan) if report else [],
            validation_limits=limits,
            candidate=candidate,
            candidate_is_historical_attempt=candidate is not None,
            difficulty=summary.difficulty if summary else None,
            relevance=summary.relevance if summary else None,
            warnings=list(summary.warnings) if summary else [],
            approval=self._approval_view(job.approval),
            error=job.error,
        )

    async def preview(self, owner_id: UUID, job_id: UUID, seed: int) -> PreviewResponse:
        """Generate one deterministic draft locally without model or MCP calls."""
        job = await self.get_job(owner_id, job_id)
        await self._require_review_evidence(job)
        _, artifact = await self._verified_artifact(job)
        question = self._generate(artifact, seed)
        if job.artifact_id is None or job.artifact_sha256 is None:
            raise AuthoringConflict("The validated artifact is unavailable.")
        return PreviewResponse(
            job_id=job.job_id,
            artifact_id=job.artifact_id,
            artifact_sha256=job.artifact_sha256,
            seed=seed,
            question=question,
        )

    async def decide(
        self,
        owner_id: UUID,
        job_id: UUID,
        request: ApprovalRequest,
    ) -> ApprovalResponse:
        """Persist the current decision when the exact artifact is usable."""
        job = await self.get_job(owner_id, job_id)
        await self._require_review_evidence(job)
        if request.artifact_sha256 != job.artifact_sha256:
            raise AuthoringConflict("The artifact changed; refresh the review before deciding.")
        await self._verified_artifact(job)
        approval = ApprovalRecord(
            decision=request.decision,
            artifact_sha256=request.artifact_sha256,
            reviewer_id=owner_id,
            reviewer=str(owner_id),
            note=request.note,
            decided_at=_now(),
        )
        updated = await asyncio.to_thread(self.store.save_approval, job_id, approval)
        view = self._approval_view(updated.approval)
        if view is None:
            raise AuthoringConflict("The approval decision could not be saved.")
        return ApprovalResponse(job_id=job_id, **view.model_dump())

    async def generate(
        self,
        owner_id: UUID,
        job_id: UUID,
        request: GenerateRequest,
    ) -> GeneratedQuestionsBatch:
        """Expand an approved artifact across consecutive deterministic seeds."""
        job = await self.get_job(owner_id, job_id)
        await self._require_review_evidence(job)
        limit = min(self.settings.max_quantity, 50)
        if request.quantity > limit:
            raise AuthoringValidationError(f"Quantity must be at most {limit} for this server.")
        if request.artifact_sha256 != job.artifact_sha256:
            raise AuthoringConflict("The artifact changed; refresh the review before generating.")
        approval = job.approval
        if (
            approval is None
            or approval.decision != "approved"
            or approval.artifact_sha256 != request.artifact_sha256
        ):
            raise AuthoringConflict(
                "The exact artifact must be approved before generating questions."
            )
        _, artifact = await self._verified_artifact(job)

        questions: list[CodeQuestionInstance] = []
        warnings: list[str] = []
        for offset in range(request.quantity):
            seed = request.seed + offset
            try:
                questions.append(self._generate_raw(artifact, seed))
            except (ValidationError, ValueError):
                warnings.append(
                    f"Seed {seed} did not produce a usable question from the "
                    "finite template domain."
                )
        fingerprints = {question.model_dump_json(exclude={"seed"}) for question in questions}
        distinct_count = len(fingerprints)
        duplicates = len(questions) - distinct_count
        if duplicates:
            warnings.append(
                f"{duplicates} duplicate question(s) came from a finite parameter "
                "domain; every retained instance still has a distinct seed."
            )
        if job.artifact_id is None or job.artifact_sha256 is None:
            raise AuthoringConflict("The validated artifact is unavailable.")
        created_at = _now()
        await asyncio.to_thread(
            self.store.save_generation,
            job.job_id,
            GenerationMetadata(
                artifact_sha256=job.artifact_sha256,
                base_seed=request.seed,
                requested_quantity=request.quantity,
                actual_quantity=len(questions),
                distinct_count=distinct_count,
                duplicates=duplicates,
                warnings=warnings,
                created_at=created_at,
            ),
        )
        return GeneratedQuestionsBatch(
            job_id=job.job_id,
            artifact_id=job.artifact_id,
            artifact_sha256=job.artifact_sha256,
            base_seed=request.seed,
            requested_quantity=request.quantity,
            actual_quantity=len(questions),
            distinct_count=distinct_count,
            duplicates=duplicates,
            questions=questions,
            warnings=warnings,
        )

    def job_status(self, job: StoredJob) -> AuthoringJobStatusResponse:
        return AuthoringJobStatusResponse(
            job_id=job.job_id,
            state=job.state,
            progress=job.progress,
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            approval=self._approval_view(job.approval),
            last_generation=job.last_generation,
        )

    def job_summary(self, job: StoredJob) -> AuthoringJobSummary:
        return AuthoringJobSummary(
            job_id=job.job_id,
            state=job.state,
            result_status=job.result.status if job.result is not None else None,
            created_at=job.created_at,
            prompt_preview=_truncate(job.request.prompt, 160),
            difficulty=job.request.difficulty,
            approval=self._approval_view(job.approval),
        )

    def _profile(self, profile_id: str) -> AuthoringProfileSettings:
        for profile in self.settings.model_profiles:
            if profile.id == profile_id:
                return profile
        raise AuthoringValidationError("Unknown model profile.")

    def _judge_model_plan(
        self,
        selection: AuthoringModelSelection | None,
        *,
        default: ModelPlan,
        credentials: ProviderCredentials | None,
        label: str,
    ) -> ModelPlan:
        """Resolve one optional advisory override, inheriting the author by default."""
        if selection is None:
            return default
        if selection.connection_id is not None:
            if credentials is None:
                raise AuthoringValidationError(
                    f"{label} model connection is unavailable."
                )
            return ModelPlan(
                selection=TemplateProviderSelection(
                    provider=credentials.provider, model=credentials.model
                ),
                credentials=credentials,
            )
        if selection.model_profile is None:
            raise AuthoringValidationError(f"Choose a {label.lower()} model.")
        profile = self._profile(selection.model_profile)
        return ModelPlan(
            selection=TemplateProviderSelection(
                provider=profile.provider, model=profile.model
            )
        )

    async def _require_review_evidence(self, job: StoredJob) -> None:
        """Require the saved report and bind its artifact to the job."""
        if job.artifact_sha256 is None:
            raise AuthoringConflict(
                "Only a technically checked artifact with saved review evidence "
                "can be previewed, approved or generated."
            )
        report = await asyncio.to_thread(self.store.read_report, job.job_id)
        require_reusable_evidence(
            job,
            expected_artifact_sha256=job.artifact_sha256,
            report=report,
        )

    async def _verified_artifact(self, job: StoredJob) -> tuple[bytes, ValidatedCodeTemplate]:
        if job.artifact_sha256 is None or job.artifact_id is None:
            raise AuthoringConflict("The validated artifact is unavailable.")
        data = await asyncio.to_thread(self.store.read_artifact, job.job_id)
        digest = hashlib.sha256(data).hexdigest()
        if digest != job.artifact_sha256:
            raise AuthoringConflict(
                "The stored artifact failed its integrity check; refresh the review."
            )
        try:
            artifact = ValidatedCodeTemplate.model_validate_json(data)
        except (ValidationError, ValueError) as exc:
            raise AuthoringConflict("The stored artifact is not usable.") from exc
        if artifact.artifact_id != job.artifact_id:
            raise AuthoringConflict("The stored artifact identity does not match.")
        return data, artifact

    @staticmethod
    def _generate_raw(artifact: ValidatedCodeTemplate, seed: int) -> CodeQuestionInstance:
        result = TemplateApplication().generate_question(
            artifact, domain=create_domain("code"), seed=seed
        )
        return CodeQuestionInstance.model_validate(result.model_dump())

    @classmethod
    def _generate(cls, artifact: ValidatedCodeTemplate, seed: int) -> CodeQuestionInstance:
        try:
            return cls._generate_raw(artifact, seed)
        except (ValidationError, ValueError) as exc:
            raise AuthoringConflict(
                "The artifact could not produce a question for this seed."
            ) from exc

    @staticmethod
    def _project_attempt(attempt: GenerationAttempt) -> ReviewAttempt:
        return ReviewAttempt(
            number=attempt.number,
            candidate=_candidate(attempt.candidate),
            pending=list(attempt.pending),
            complete=attempt.complete,
            passed=attempt.passed,
            checks=[_project_check(execution) for execution in attempt.executions],
        )

    @staticmethod
    def _limits(validation: TemplateValidationSummary) -> ValidationLimits:
        return ValidationLimits(
            validator_version=validation.validator_version,
            checking_mode=validation.checking_mode,
            examples_checked=validation.examples_checked,
            execution_calls=validation.execution_calls,
            max_examples=validation.max_examples,
            max_execution_calls=validation.max_execution_calls,
            timeout_seconds=validation.timeout_seconds,
            seed=validation.seed,
        )

    @staticmethod
    def _approval_view(approval: ApprovalRecord | None) -> ApprovalView | None:
        if approval is None:
            return None
        return ApprovalView(
            decision=approval.decision,
            artifact_sha256=approval.artifact_sha256,
            reviewer=approval.reviewer,
            note=approval.note,
            decided_at=approval.decided_at,
        )


def _project_check(execution: Any) -> ReviewCheck:
    evidence = execution.evidence
    if evidence is not None:
        status = evidence.status
        findings = [
            ReviewFinding(
                code=finding.code,
                message=_truncate(finding.message, MAX_FINDING_TEXT),
                field=finding.field,
            )
            for finding in evidence.findings
        ]
        advisory = execution.advisory or evidence.details.get("advisory") is True
    else:
        status = "error" if execution.error is not None else "skipped"
        findings = []
        advisory = bool(execution.advisory)
    return ReviewCheck(
        tool=execution.tool,
        status=status,
        advisory=advisory,
        findings=findings,
        error="Check did not complete." if execution.error is not None else None,
    )


def _candidate(value: Any) -> CodeTemplateCandidate | None:
    try:
        return CodeTemplateCandidate.model_validate(value)
    except (ValidationError, ValueError):
        return None


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "...<truncated>"


def _now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "AiAuthoringService",
    "AuthoringNotFound",
    "AuthoringStorageUnavailable",
    "AuthoringValidationError",
    "LIBRARY_REVISION",
]
