"""Deterministic, model-free fixtures for AI authoring tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from edcraft_validator.application.authoring_api import (
    AuthoringJobCommand,
    AuthoringJobRecord,
    AuthoringJobResponse,
    run_authoring_job_sync,
    summarize_authoring,
)
from edcraft_validator.application.authoring_contracts import (
    AuthoringProgress,
    AuthoringResult,
    CheckExecution,
    GenerationAttempt,
)
from edcraft_validator.application.template_workflow import TemplateApplication
from edcraft_validator.domains.code.code_schemas import (
    CodeQuestionInstance,
    CodeTemplateCandidate,
    CodeTemplateProposal,
    TemplateValidationSummary,
    ValidatedCodeTemplate,
)
from edcraft_validator.domains.domain_registry import create_domain
from edcraft_validator.llm.llm_contracts import PlannedGenerationResponse
from edcraft_validator.validation.check_contracts import ToolEvidence, ToolFinding
from edcraft_validator.validation.validation_contracts import ValidationEvidence

CANDIDATE: dict[str, Any] = {
    "template_id": "arithmetic.linear_sum",
    "topic": "arithmetic",
    "difficulty": "easy",
    "code": "def calculate(a, b, c):\n    return a + b - c",
    "entry_function": "calculate",
    "parameters": [
        {"name": "a", "kind": "integer", "values": [2, 4]},
        {"name": "b", "kind": "integer", "values": [5, 8]},
        {"name": "c", "kind": "integer", "values": [1, 3]},
    ],
    "question_template": "What does calculate({a}, {b}, {c}) return?",
    "answer_target": "return_value",
    "answer_expression": "a + b - c",
    "distractors": [
        {
            "expression": "a + b + c",
            "reason_template": "Adds c instead of subtracting it.",
        },
        {
            "expression": "a - b - c",
            "reason_template": "Subtracts both b and c from a.",
        },
        {"expression": "a + b", "reason_template": "Omits the final subtraction of c."},
    ],
    "question_type": "mcq",
}

PROPOSAL_FIELDS = (
    "question_template",
    "code",
    "entry_function",
    "parameters",
    "answer_target",
    "answer_expression",
    "distractors",
)


def proposal() -> CodeTemplateProposal:
    return CodeTemplateProposal.model_validate(
        {key: CANDIDATE[key] for key in PROPOSAL_FIELDS}
    )


class ScriptedProvider:
    """Return one known proposal and one technical check without a model."""

    provider = "stub"
    model = "stub-model"

    def generation_settings(self) -> dict[str, Any]:
        return {"mode": "scripted"}

    def generate(self, request: Any) -> PlannedGenerationResponse[Any]:
        assert request.response_model
        return PlannedGenerationResponse(
            proposal=proposal(),
            checks=[
                {"name": "code_validate_answers_and_distractors", "arguments": {}}
            ],
        )


def run_scripted_pipeline(
    command: AuthoringJobCommand,
    on_progress: Callable[[AuthoringProgress], None] | None = None,
) -> AuthoringJobRecord:
    """Run the real library workflow with a scripted provider and real MCP checks."""
    return run_authoring_job_sync(
        command,
        provider_factory=lambda selection: ScriptedProvider(),
        on_progress=on_progress,
    )


def make_command(job_id: UUID | None = None) -> AuthoringJobCommand:
    return AuthoringJobCommand(
        job_id=job_id or uuid4(),
        domain="code",
        author={"provider": "stub", "model": "stub-model"},
        request={
            "prompt": "Create an arithmetic tracing question",
            "difficulty": "easy",
            "num_distractors": 3,
        },
    )


def _evidence(tool: str, status: str, **details: Any) -> ToolEvidence:
    findings = (
        []
        if status == "passed"
        else [ToolFinding(code="TECHNICAL_FAILURE", message="Check did not pass.")]
    )
    return ToolEvidence(
        tool=tool,
        version="1.0.0",
        status=status,
        findings=findings,
        details=details,
    )


def make_checked_report(
    command: AuthoringJobCommand,
    *,
    advisory_failure: bool = False,
    advisory_unavailable: bool = False,
    technical_failure: bool = False,
) -> AuthoringResult:
    """Build a real validated artifact with safe, inspectable review evidence."""
    technical_status = "failed" if technical_failure else "passed"
    candidate = CodeTemplateCandidate.model_validate(CANDIDATE)
    validation = TemplateValidationSummary(
        checking_mode="property_based",
        examples_checked=4,
        execution_calls=4,
        max_examples=20,
        max_execution_calls=20,
        timeout_seconds=2.0,
        seed=0,
        evidence=[
            ValidationEvidence(
                check="code_validate_answers_and_distractors", status="passed"
            )
        ],
    )
    artifact = ValidatedCodeTemplate(
        artifact_id=uuid4().hex,
        template=candidate,
        validation=validation,
    )
    checks = [
        CheckExecution(
            call_id="attempt-1:code_validate_answers_and_distractors",
            tool="code_validate_answers_and_distractors",
            advisory=False,
            requested_arguments={},
            evidence=_evidence(
                "code_validate_answers_and_distractors", technical_status
            ),
        )
    ]
    if advisory_failure:
        checks.append(
            CheckExecution(
                call_id="attempt-1:code_assess_template_difficulty",
                tool="code_assess_template_difficulty",
                advisory=True,
                requested_arguments={},
                evidence=_evidence(
                    "code_assess_template_difficulty",
                    "failed",
                    advisory=True,
                    difficulty_outcome={
                        "assessment_path": "decision",
                        "requested_difficulty": "easy",
                        "estimated_difficulty": "hard",
                        "decision": "advisory_mismatch",
                        "status": "failed",
                        "reason": "Advisory estimate differs from the target.",
                    },
                ),
            )
        )
    elif advisory_unavailable:
        checks.append(
            CheckExecution(
                call_id="attempt-1:code_assess_template_difficulty",
                tool="code_assess_template_difficulty",
                advisory=True,
                requested_arguments={},
                error="raw advisory transport failure",
            )
        )
    attempt = GenerationAttempt(
        number=1,
        candidate=candidate.model_dump(mode="json"),
        executions=checks,
        pending=[],
        complete=True,
        passed=not technical_failure,
    )
    return AuthoringResult(
        status="checked",
        provider="stub",
        model="stub-model",
        domain="code",
        provider_settings={"api_key": "never-return-this"},
        request=command.request,
        prompt_version="scripted-v1",
        fixed_plan=[check.tool for check in checks],
        tool_catalogue=[],
        attempts=[attempt],
        artifact=artifact,
        reason="raw exception text must never be returned",
    )


def make_needs_review_report(command: AuthoringJobCommand) -> AuthoringResult:
    execution = CheckExecution(
        call_id="attempt-1:code_validate_answers_and_distractors",
        tool="code_validate_answers_and_distractors",
        advisory=False,
        requested_arguments={},
        evidence=_evidence("code_validate_answers_and_distractors", "failed"),
    )
    attempt = GenerationAttempt(
        number=1,
        candidate=CodeTemplateCandidate.model_validate(CANDIDATE).model_dump(
            mode="json"
        ),
        executions=[execution],
        pending=[],
        complete=True,
        passed=False,
    )
    return AuthoringResult(
        status="needs_review",
        provider="stub",
        model="stub-model",
        domain="code",
        provider_settings={"api_key": "never-return-this"},
        request=command.request,
        prompt_version="scripted-v1",
        fixed_plan=[execution.tool],
        tool_catalogue=[],
        attempts=[attempt],
        reason="raw check failure text must never be returned",
    )


class StaticExecutor:
    """Return a prebuilt report for the exact submitted command."""

    def __init__(self, report_factory: Callable[[AuthoringJobCommand], AuthoringResult]):
        self._factory = report_factory
        self.calls = 0

    def __call__(
        self,
        command: AuthoringJobCommand,
        on_progress: Callable[[AuthoringProgress], None] | None,
    ) -> AuthoringJobRecord:
        self.calls += 1
        report = self._factory(command)
        if on_progress is not None:
            on_progress(AuthoringProgress(phase="generating", attempt=1))
            on_progress(AuthoringProgress(phase="checking", attempt=1))
        summary = summarize_authoring(report)
        return AuthoringJobRecord(
            response=AuthoringJobResponse(
                job_id=command.job_id,
                state="failed" if report.status == "error" else "completed",
                result=summary,
            ),
            report=report,
        )


def generate(artifact: ValidatedCodeTemplate, seed: int) -> CodeQuestionInstance:
    result = TemplateApplication().generate_question(
        artifact, domain=create_domain("code"), seed=seed
    )
    return CodeQuestionInstance.model_validate(result.model_dump())
