"""Construct validator model providers from per-job user credentials."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edcraft_validator.llm.forced_decision import ClassDecision
from edcraft_validator.llm.llm_contracts import (
    ModelProvider,
    StructuredGenerationRequest,
)
from edcraft_validator.llm.openai_compatible_provider import (
    OpenAIProvider,
    SocLaasProvider,
)
from openai import OpenAI

DEFAULT_TIMEOUT_SECONDS = {
    "soclaas": 300.0,
    "openai": 120.0,
}


@dataclass(frozen=True, slots=True)
class ProviderCredentials:
    """Non-persisted credentials resolved for exactly one authoring job."""

    provider: str
    model: str
    api_key: str
    base_url: str | None

    @property
    def timeout_seconds(self) -> float:
        return DEFAULT_TIMEOUT_SECONDS.get(self.provider, 120.0)


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
    client = OpenAI(
        api_key=credentials.api_key,
        base_url=credentials.base_url,
        timeout=credentials.timeout_seconds,
        max_retries=1,
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
