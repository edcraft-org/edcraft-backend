"""Resolve the authoring model roles and run one job behind a single runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from edcraft_validator.application.authoring_api import (
    AuthoringJobCommand,
    AuthoringJobRecord,
)
from edcraft_validator.application.authoring_contracts import AuthoringProgress
from edcraft_validator.llm.llm_contracts import TemplateProviderSelection

from edcraft_backend.config.settings import AuthoringProfileSettings
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.schemas.ai_authoring import (
    AuthoringModelSelection,
    SubmitAuthoringJobRequest,
)
from edcraft_backend.services.ai_authoring_providers import (
    DEFAULT_TIMEOUT_SECONDS,
    ManagedProvider,
)
from edcraft_backend.services.provider_endpoint import ProviderEndpoint

ProgressCallback = Callable[[AuthoringProgress], None]


class AuthoringValidationError(EdCraftBaseException):
    """The requested model configuration cannot form an authoring job."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 422)


class JobExecutor(Protocol):
    """Synchronous library boundary executed inside a worker thread."""

    def __call__(
        self,
        command: AuthoringJobCommand,
        runtime: JobRuntime,
        on_progress: ProgressCallback | None,
    ) -> AuthoringJobRecord: ...


@dataclass(frozen=True, slots=True)
class ResolvedConnection:
    """One role's provider selection, with a BYOK secret when it has one.

    A role without a secret uses a server-configured profile, so the same
    value carries both branches and the runtime never has to branch again.
    """

    selection: TemplateProviderSelection
    connection_id: UUID | None = None
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None

    @classmethod
    def for_profile(cls, profile: AuthoringProfileSettings) -> ResolvedConnection:
        """Resolve a server profile into a role with no per-job secret."""
        return cls(
            selection=TemplateProviderSelection(
                provider=profile.provider, model=profile.model
            )
        )

    @classmethod
    def for_connection(
        cls,
        *,
        connection_id: UUID,
        provider: str,
        model: str,
        api_key: str,
        base_url: str,
    ) -> ResolvedConnection:
        """Resolve one owner-scoped connection into a role with a BYOK secret."""
        return cls(
            selection=TemplateProviderSelection(provider=provider, model=model),
            connection_id=connection_id,
            api_key=api_key,
            base_url=base_url,
        )

    @property
    def is_byok(self) -> bool:
        """Whether this role carries a per-job secret instead of a profile."""
        return self.api_key is not None

    @property
    def model(self) -> str:
        """The role's model name; every authoring role must name one."""
        model = self.selection.model
        if not isinstance(model, str):
            raise ValueError("The authoring role must name a model.")
        return model

    def open_provider(self) -> ManagedProvider:
        """Build a fresh provider; the secret stays inside this value."""
        if self.api_key is None:
            raise ValueError("A server profile does not carry a provider secret.")
        endpoint = ProviderEndpoint.parse(self.selection.provider, self.base_url)
        return endpoint.open_provider(
            self.api_key,
            self.model,
            timeout_seconds=DEFAULT_TIMEOUT_SECONDS.get(
                self.selection.provider, 120.0
            ),
        )


class JobRuntime:
    """The three resolved model roles for exactly one authoring job."""

    def __init__(
        self,
        *,
        author: ResolvedConnection,
        difficulty: ResolvedConnection,
        relevance: ResolvedConnection,
        executor: JobExecutor,
    ) -> None:
        self.author = author
        self.difficulty = difficulty
        self.relevance = relevance
        self._executor = executor

    @classmethod
    def prepare(
        cls,
        request: SubmitAuthoringJobRequest,
        *,
        profile_lookup: Callable[[str], AuthoringProfileSettings],
        executor: JobExecutor,
        author_connection: ResolvedConnection | None = None,
        difficulty_connection: ResolvedConnection | None = None,
        relevance_connection: ResolvedConnection | None = None,
    ) -> JobRuntime:
        """Resolve all three roles from the request and pre-resolved connections."""
        author = cls._author_role(
            request, profile_lookup=profile_lookup, connection=author_connection
        )
        judges = request.judges
        return cls(
            author=author,
            difficulty=cls._judge_role(
                judges.difficulty if judges else None,
                default=author,
                connection=difficulty_connection,
                profile_lookup=profile_lookup,
                label="Difficulty",
            ),
            relevance=cls._judge_role(
                judges.relevance if judges else None,
                default=author,
                connection=relevance_connection,
                profile_lookup=profile_lookup,
                label="Relevance",
            ),
            executor=executor,
        )

    def run(
        self,
        command: AuthoringJobCommand,
        on_progress: ProgressCallback | None = None,
    ) -> AuthoringJobRecord:
        """Run the validator through the injected executor seam."""
        return self._executor(command, self, on_progress)

    @staticmethod
    def _author_role(
        request: SubmitAuthoringJobRequest,
        *,
        profile_lookup: Callable[[str], AuthoringProfileSettings],
        connection: ResolvedConnection | None,
    ) -> ResolvedConnection:
        if request.connection_id is not None:
            if connection is None:
                raise AuthoringValidationError("Model connection is unavailable.")
            return connection
        if request.model_profile is None:
            raise AuthoringValidationError("Choose a question-writing model.")
        return ResolvedConnection.for_profile(profile_lookup(request.model_profile))

    @staticmethod
    def _judge_role(
        selection: AuthoringModelSelection | None,
        *,
        default: ResolvedConnection,
        connection: ResolvedConnection | None,
        profile_lookup: Callable[[str], AuthoringProfileSettings],
        label: str,
    ) -> ResolvedConnection:
        """Resolve one advisory override, inheriting the author by default."""
        if selection is None:
            return default
        if selection.connection_id is not None:
            if connection is None:
                raise AuthoringValidationError(
                    f"{label} model connection is unavailable."
                )
            return connection
        if selection.model_profile is None:
            raise AuthoringValidationError(f"Choose a {label.lower()} model.")
        return ResolvedConnection.for_profile(profile_lookup(selection.model_profile))


__all__ = [
    "AuthoringValidationError",
    "JobExecutor",
    "JobRuntime",
    "ProgressCallback",
    "ResolvedConnection",
]
