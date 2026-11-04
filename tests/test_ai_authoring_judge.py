"""Verify advisory judges follow the model selected for each authoring job."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from edcraft_validator.llm.forced_decision import ClassDecision
from edcraft_validator.llm.llm_contracts import TemplateProviderSelection

from edcraft_backend.services import ai_authoring_judge, ai_authoring_runner
from edcraft_backend.services.ai_authoring_judge import (
    SelectedModelDecisionProvider,
    build_credential_tool_client,
    build_profile_tool_client,
    build_selected_model_tool_client,
    judge_settings_for,
)
from edcraft_backend.services.ai_authoring_providers import (
    ManagedProvider,
    ProviderCredentials,
)
from tests.ai_authoring_helpers import make_command


class StubProvider:
    """Minimal provider that records forced classification calls."""

    def __init__(
        self, *, provider: str = "openai", model: str = "gpt-4.1-mini"
    ) -> None:
        self.provider = provider
        self.model = model
        self.decisions: list[tuple[list[dict], tuple[str, ...]]] = []

    def generation_settings(self) -> dict[str, str]:
        return {"provider": self.provider, "model": self.model}

    def generate(self, request):  # pragma: no cover - not used by judges
        raise AssertionError("Judge wiring must not generate proposals")

    def decide(self, messages, labels) -> ClassDecision:
        self.decisions.append((messages, labels))
        return ClassDecision(
            label="yes",
            distribution={"yes": 0.8, "no": 0.2},
            confidence=0.8,
            served_model=self.model,
        )


def test_managed_provider_forwards_decisions_and_usage() -> None:
    delegate = StubProvider()
    delegate.last_usage = {"input_tokens": 5}
    client = SimpleNamespace(close=lambda: None)
    provider = ManagedProvider(
        delegate, client, provider="openai", model="gpt-4.1-mini"
    )

    decision = provider.decide([], ("yes", "no"))

    assert decision.label == "yes"
    assert provider.last_usage == {"input_tokens": 5}


def test_managed_provider_rejects_delegates_without_decisions() -> None:
    class NoDecisions:
        pass

    provider = ManagedProvider(
        NoDecisions(), SimpleNamespace(close=lambda: None), provider="openai", model="x"
    )

    with pytest.raises(ValueError, match="token-probability"):
        provider.decide([], ("yes", "no"))


def test_judge_settings_for_keeps_server_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDCRAFT_RELEVANCE_THRESHOLD", "0.75")
    monkeypatch.setenv("EDCRAFT_JUDGE_REASONING_EFFORT", "high")

    settings = judge_settings_for("openai", "gpt-4.1-mini")

    assert settings.provider == "openai"
    assert settings.model == "gpt-4.1-mini"
    assert settings.relevance_threshold == 0.75
    assert settings.reasoning_effort == "high"


def test_selected_model_decision_provider_scores_with_job_model() -> None:
    settings = judge_settings_for("openai", "gpt-4.1-mini")
    provider = StubProvider()

    decision_provider = SelectedModelDecisionProvider(settings, provider)

    assert decision_provider.provider == "openai"
    assert decision_provider.model == "gpt-4.1-mini"
    assert decision_provider.threshold == settings.relevance_threshold
    assert decision_provider.score("build a loop", "write a loop") == pytest.approx(0.8)
    assert decision_provider.served_model == "gpt-4.1-mini"
    assert provider.decisions[0][1] == ("yes", "no")


def test_selected_model_decision_provider_rejects_providers_without_decisions() -> None:
    class NoDecisions:
        provider = "openai"
        model = "gpt-4.1-mini"

        def generation_settings(self) -> dict[str, str]:
            return {}

    with pytest.raises(ValueError, match="token-probability"):
        SelectedModelDecisionProvider(
            judge_settings_for("openai", "gpt-4.1-mini"), NoDecisions()
        )


def test_selected_model_tool_client_wires_both_judges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}
    server = object()

    def fake_server(**kwargs):
        captured.update(kwargs)
        return server

    monkeypatch.setattr(ai_authoring_judge, "create_validation_server", fake_server)
    monkeypatch.setattr(
        ai_authoring_judge,
        "FastMcpToolClient",
        lambda created: SimpleNamespace(server=created),
    )
    provider = StubProvider()

    client = build_selected_model_tool_client(
        provider="openai",
        model="gpt-4.1-mini",
        provider_factory=lambda: provider,
    )

    assert client.server is server
    assert captured["judge_settings"].provider == "openai"
    assert captured["judge_settings"].model == "gpt-4.1-mini"
    assert captured["difficulty_provider_factory"]() is provider

    decision_provider = captured["decision_provider_factory"]()
    assert decision_provider.delegate is provider
    assert decision_provider.provider == "openai"
    assert decision_provider.model == "gpt-4.1-mini"


def test_credential_tool_client_uses_the_caller_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials = ProviderCredentials(
        provider="openai",
        model="gpt-4.1-mini",
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
    )
    managed = StubProvider()
    captured: dict = {}

    monkeypatch.setattr(
        ai_authoring_judge, "build_managed_provider", lambda _credentials: managed
    )
    monkeypatch.setattr(
        ai_authoring_judge,
        "build_selected_model_tool_client",
        lambda **kwargs: captured.update(kwargs) or "client",
    )

    assert build_credential_tool_client(credentials) == "client"
    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["provider_factory"]() is managed


def test_profile_tool_client_uses_the_profile_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = TemplateProviderSelection(provider="soclaas", model="x-test-2")
    managed = StubProvider(provider="soclaas", model="x-test-2")
    captured: dict = {}

    monkeypatch.setattr(
        ai_authoring_judge, "create_model_provider", lambda _selection: managed
    )
    monkeypatch.setattr(
        ai_authoring_judge,
        "build_selected_model_tool_client",
        lambda **kwargs: captured.update(kwargs) or "client",
    )

    assert build_profile_tool_client(selection) == "client"
    assert captured["provider"] == "soclaas"
    assert captured["model"] == "x-test-2"
    assert captured["provider_factory"]() is managed


def test_profile_tool_client_requires_a_named_model() -> None:
    with pytest.raises(ValueError, match="must name a model"):
        build_profile_tool_client(TemplateProviderSelection(provider="soclaas"))


def test_runner_profile_path_builds_the_tool_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = make_command()
    tool_client = object()
    record = object()
    captured: dict = {}

    def fake_run(_command, **kwargs):
        captured.update(kwargs)
        return record

    monkeypatch.setattr(
        ai_authoring_runner, "build_profile_tool_client", lambda _selection: tool_client
    )
    monkeypatch.setattr(ai_authoring_runner, "run_authoring_job_sync", fake_run)
    monkeypatch.setattr(
        ai_authoring_runner,
        "TemplateApplication",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    result = ai_authoring_runner.run_library_authoring_job(command, None, None)

    assert result is record
    assert captured["application_factory"]().tool_client is tool_client
    assert "provider_factory" not in captured


def test_runner_credentials_path_shares_the_selected_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = make_command()
    credentials = ProviderCredentials(
        provider="openai",
        model="gpt-4.1-mini",
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
    )
    tool_client = object()
    managed = object()
    record = object()
    captured: dict = {}

    def fake_run(_command, **kwargs):
        captured.update(kwargs)
        return record

    monkeypatch.setattr(
        ai_authoring_runner,
        "build_credential_tool_client",
        lambda resolved: tool_client if resolved is credentials else None,
    )
    monkeypatch.setattr(
        ai_authoring_runner, "build_managed_provider", lambda _credentials: managed
    )
    monkeypatch.setattr(ai_authoring_runner, "run_authoring_job_sync", fake_run)
    monkeypatch.setattr(
        ai_authoring_runner,
        "TemplateApplication",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    result = ai_authoring_runner.run_library_authoring_job(command, credentials, None)

    assert result is record
    assert captured["application_factory"]().tool_client is tool_client
    assert captured["provider_factory"](command.author) is managed
