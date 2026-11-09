"""Business rules for owner-scoped AI authoring, review and generation."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from edcraft_validator.application.authoring_api import AuthoringJobCommand
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
from pydantic import ValidationError

from edcraft_backend.config.settings import AuthoringProfileSettings, AuthoringSettings
from edcraft_backend.schemas.ai_authoring import (
    ApprovalRequest,
    ApprovalResponse,
    AuthoringCapabilitiesResponse,
    AuthoringJobStatusResponse,
    AuthoringJobSummary,
    AuthoringModelProfile,
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
from edcraft_backend.services.ai_authoring_lifecycle import AuthoringLifecycle
from edcraft_backend.services.ai_authoring_runner import run_library_authoring_job
from edcraft_backend.services.ai_authoring_runtime import (
    AuthoringValidationError,
    JobExecutor,
    JobRuntime,
)
from edcraft_backend.services.ai_authoring_store import (
    ApprovalRecord,
    AuthoringConflict,
    AuthoringNotFound,
    AuthoringRequestRecord,
    AuthoringStorageUnavailable,
    AuthoringStore,
    EvidenceRequirement,
    StoredJob,
)
from edcraft_backend.services.provider_endpoint import ResolvedConnection

ApprovalView = StoredReviewerApproval

logger = logging.getLogger(__name__)

# Must match [tool.uv.sources].edcraft-validator.rev in pyproject.toml.
LIBRARY_REVISION = "a7326fc30b33ce1b71f7d836d152df5145f135b8"
MAX_FINDING_TEXT = 2_000


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
        self._executor: JobExecutor = executor or run_library_authoring_job
        self.lifecycle = AuthoringLifecycle(self.store, settings)

    async def startup(self) -> None:
        """Prepare storage, reconcile interruptions and bind the lifecycle."""
        await self.lifecycle.start()

    async def shutdown(self, timeout: float | None = None) -> None:
        """Allow admitted work a bounded chance to finish before process exit."""
        await self.lifecycle.shutdown(
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
        *,
        author_connection: ResolvedConnection | None = None,
        difficulty_connection: ResolvedConnection | None = None,
        relevance_connection: ResolvedConnection | None = None,
    ) -> StoredJob:
        """Admit and persist one queued authoring job."""
        runtime = JobRuntime.prepare(
            request,
            profile_lookup=self._profile,
            executor=self._executor,
            author_connection=author_connection,
            difficulty_connection=difficulty_connection,
            relevance_connection=relevance_connection,
        )
        author = runtime.author
        provider = author.selection.provider
        model = author.model
        connection_id = request.connection_id
        profile_id = request.model_profile if connection_id is None else None

        job_id = uuid4()
        now = _now()
        command = AuthoringJobCommand(
            job_id=job_id,
            domain="code",
            author=author.selection,
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
        return await self.lifecycle.submit(job, command, runtime)

    async def list_jobs(self, owner_id: UUID) -> list[StoredJob]:
        return await asyncio.to_thread(self.store.list_jobs, owner_id)

    async def get_job(self, owner_id: UUID, job_id: UUID) -> StoredJob:
        return await asyncio.to_thread(self.store.get_owned_job, job_id, owner_id)

    async def wait_for_idle(self) -> None:
        """Expose deterministic completion to focused tests."""
        await self.lifecycle.wait_for_idle()

    async def review(self, owner_id: UUID, job_id: UUID) -> AuthoringReviewResponse:
        """Return sanitized evidence sufficient for an educator decision."""
        job = await self.get_job(owner_id, job_id)
        report: AuthoringResult | None = None
        artifact: ValidatedCodeTemplate | None = None
        if job.artifact_sha256 and job.artifact_id:
            evidence = await asyncio.to_thread(
                self.store.read_evidence,
                job_id,
                owner_id=owner_id,
                requirement=EvidenceRequirement.REVIEW,
            )
            job = evidence.job
            report = evidence.report
            artifact = evidence.artifact
        elif job.state in {"completed", "failed"}:
            try:
                report = await asyncio.to_thread(self.store.read_report, job_id)
            except AuthoringConflict:
                report = None

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
        evidence = await asyncio.to_thread(
            self.store.read_evidence,
            job_id,
            owner_id=owner_id,
            requirement=EvidenceRequirement.REUSABLE,
        )
        job = evidence.job
        question = self._generate(evidence.artifact, seed)
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
        await asyncio.to_thread(
            self.store.read_evidence,
            job_id,
            owner_id=owner_id,
            requirement=EvidenceRequirement.REUSABLE,
            expected_artifact_sha256=request.artifact_sha256,
        )
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
        limit = min(self.settings.max_quantity, 50)
        if request.quantity > limit:
            raise AuthoringValidationError(f"Quantity must be at most {limit} for this server.")
        evidence = await asyncio.to_thread(
            self.store.read_evidence,
            job_id,
            owner_id=owner_id,
            requirement=EvidenceRequirement.APPROVED,
            expected_artifact_sha256=request.artifact_sha256,
        )
        job = evidence.job
        artifact = evidence.artifact

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
