"""Bounded in-process runner for the pinned AI authoring library."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from edcraft_validator.application.authoring_api import (
    AuthoringJobCommand,
    AuthoringJobRecord,
    run_authoring_job_sync,
)
from edcraft_validator.application.authoring_contracts import AuthoringProgress
from edcraft_validator.application.template_workflow import TemplateApplication

from edcraft_backend.services.ai_authoring_judge import build_model_tool_client
from edcraft_backend.services.ai_authoring_providers import JobModelPlan
from edcraft_backend.services.provider_endpoint import build_managed_provider

ProgressCallback = Callable[[AuthoringProgress], None]


class JobExecutor(Protocol):
    """Synchronous library boundary executed inside a worker thread."""

    def __call__(
        self,
        command: AuthoringJobCommand,
        plan: JobModelPlan,
        on_progress: ProgressCallback | None,
    ) -> AuthoringJobRecord: ...


def run_library_authoring_job(
    command: AuthoringJobCommand,
    plan: JobModelPlan,
    on_progress: ProgressCallback | None,
) -> AuthoringJobRecord:
    """Run the validator with separately selected author and advisory models."""
    tool_client = build_model_tool_client(
        difficulty=plan.difficulty,
        relevance=plan.relevance,
    )

    def application_factory() -> TemplateApplication:
        return TemplateApplication(tool_client=tool_client)

    if plan.author.credentials is None:
        return run_authoring_job_sync(
            command,
            application_factory=application_factory,
            on_progress=on_progress,
        )
    credentials = plan.author.credentials
    return run_authoring_job_sync(
        command,
        application_factory=application_factory,
        provider_factory=lambda _selection: build_managed_provider(credentials),
        on_progress=on_progress,
    )


__all__ = [
    "JobExecutor",
    "ProgressCallback",
    "run_library_authoring_job",
]
