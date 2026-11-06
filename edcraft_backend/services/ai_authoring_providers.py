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
from edcraft_validator.llm.openai_compatible_provider import (
    OpenAIProvider,
    SocLaasProvider,
)
from openai import DefaultHttpxClient, OpenAI

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


def build_managed_provider(credentials: ProviderCredentials) -> ManagedProvider:
    """Build a fresh provider for one job; secrets stay in this closure."""
    if credentials.base_url:
        # Apply the same resolved-host guard used for provider probing so a
        # stored hostname cannot be rebound to a private address at job time.
        # Imported locally because provider_connection_service imports
        # ProviderCredentials from this module.
        from edcraft_backend.services.provider_connection_service import (
            _assert_public_provider_host,
        )

        _assert_public_provider_host(credentials.base_url)
    client = OpenAI(
        api_key=credentials.api_key,
        base_url=credentials.base_url,
        timeout=credentials.timeout_seconds,
        max_retries=1,
        # Base URLs are user-supplied. A redirect could otherwise point the
        # SDK at a private address after the guard above has passed.
        http_client=DefaultHttpxClient(follow_redirects=False),
    )
    if credentials.provider == "soclaas":
        delegate: ModelProvider = SocLaasProvider(client=client, model=credentials.model)
    elif credentials.provider == "openai":
        delegate = OpenAIProvider(client=client, model=credentials.model)
    else:
        client.close()
        raise ValueError(f"Unsupported provider: {credentials.provider}")
    return ManagedProvider(
        delegate,
        client,
        provider=credentials.provider,
        model=credentials.model,
    )
