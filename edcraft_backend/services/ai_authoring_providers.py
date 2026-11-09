"""Construct validator model providers from per-job user credentials."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from edcraft_validator.llm.forced_decision import ClassDecision
from edcraft_validator.llm.llm_contracts import (
    ModelProvider,
    StructuredGenerationRequest,
    TemplateProviderSelection,
)
from openai import OpenAI

DEFAULT_TIMEOUT_SECONDS = {
    "soclaas": 600.0,
    "openai": 120.0,
}


@dataclass(frozen=True, slots=True)
class ProviderCredentials:
    """Non-persisted credentials resolved for exactly one authoring job."""

    provider: str
    model: str
    api_key: str = field(repr=False)
    base_url: str | None

    @property
    def timeout_seconds(self) -> float:
        return DEFAULT_TIMEOUT_SECONDS.get(self.provider, 120.0)


@dataclass(frozen=True, slots=True)
class ModelPlan:
    """One resolved model role; credentials stay in memory only."""

    selection: TemplateProviderSelection
    credentials: ProviderCredentials | None = None


@dataclass(frozen=True, slots=True)
class JobCredentials:
    """Credentials resolved from the request; omitted roles inherit the author."""

    author: ProviderCredentials | None = None
    difficulty: ProviderCredentials | None = None
    relevance: ProviderCredentials | None = None


@dataclass(frozen=True, slots=True)
class JobModelPlan:
    """Author and advisory roles for exactly one authoring job."""

    author: ModelPlan
    difficulty: ModelPlan
    relevance: ModelPlan


class ManagedProvider:
    """Adapt a validator provider and own its OpenAI client lifecycle."""

    def __init__(
        self,
        delegate: ModelProvider,
        client: OpenAI,
        *,
        provider: str,
        model: str,
    ) -> None:
        self._delegate = delegate
        self._client = client
        self.provider = provider
        self.model = model

    def generation_settings(self) -> dict[str, Any]:
        settings: dict[str, Any] = self._delegate.generation_settings()
        return settings

    def generate(self, request: StructuredGenerationRequest[Any]) -> Any:
        return self._delegate.generate(request)

    def decide(
        self, messages: list[dict[str, Any]], labels: tuple[str, ...]
    ) -> ClassDecision:
        """Expose the delegate's forced classification for advisory checks."""
        decide = getattr(self._delegate, "decide", None)
        if not callable(decide):
            raise ValueError("Provider does not support token-probability decisions")
        decision: ClassDecision = decide(messages, labels)
        return decision

    @property
    def last_usage(self) -> Any:
        """Forward provider usage so relevance evidence stays complete."""
        return getattr(self._delegate, "last_usage", None)

    def close(self) -> None:
        self._client.close()

