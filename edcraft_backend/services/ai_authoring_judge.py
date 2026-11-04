"""Wire advisory judges to the model selected for one authoring job."""

from __future__ import annotations

from collections.abc import Callable

from edcraft_validator.llm.decision import ConfiguredDecisionProvider
from edcraft_validator.llm.judge_configuration import JudgeSettings, load_judge_settings
from edcraft_validator.llm.llm_contracts import (
    ModelProvider,
    TemplateProviderSelection,
    supports_decisions,
)
from edcraft_validator.llm.provider_registry import create_model_provider
from edcraft_validator.mcp.client import FastMcpToolClient
from edcraft_validator.mcp.server import create_validation_server

from edcraft_backend.services.ai_authoring_providers import (
    ProviderCredentials,
    build_managed_provider,
)


class SelectedModelDecisionProvider(ConfiguredDecisionProvider):
    """Relevance classifier that reuses the provider chosen for the job."""

    def __init__(self, settings: JudgeSettings, provider: ModelProvider) -> None:
        if not supports_decisions(provider):
            raise ValueError("Provider does not support token-probability decisions")
        self.settings = settings
        self.delegate = provider
        self.provider = provider.provider
        self.model = provider.model
        self.threshold = settings.relevance_threshold
        self.served_model = None


def judge_settings_for(provider: str, model: str) -> JudgeSettings:
    """Keep server thresholds and timeouts while judging with the selected model."""
    return load_judge_settings().model_copy(
        update={"provider": provider, "model": model}
    )


def build_selected_model_tool_client(
    *,
    provider: str,
    model: str,
    provider_factory: Callable[[], ModelProvider],
) -> FastMcpToolClient:
    """Build the validation tools with difficulty and relevance on one model."""
    settings = judge_settings_for(provider, model)
    return FastMcpToolClient(
        create_validation_server(
            judge_settings=settings,
            difficulty_provider_factory=provider_factory,
            decision_provider_factory=lambda: SelectedModelDecisionProvider(
                settings, provider_factory()
            ),
        )
    )


def build_credential_tool_client(credentials: ProviderCredentials) -> FastMcpToolClient:
    """Use the caller's own credentials for every model call in the job."""
    return build_selected_model_tool_client(
        provider=credentials.provider,
        model=credentials.model,
        provider_factory=lambda: build_managed_provider(credentials),
    )


def build_profile_tool_client(selection: TemplateProviderSelection) -> FastMcpToolClient:
    """Use the profile's server-side credentials for authoring and judging."""
    model = selection.model
    if model is None:
        raise ValueError("A server model profile must name a model")
    return build_selected_model_tool_client(
        provider=selection.provider,
        model=model,
        provider_factory=lambda: create_model_provider(selection),
    )
