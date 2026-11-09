"""Provider construction guards for user-supplied base URLs."""

from __future__ import annotations

from typing import Any

import pytest

from edcraft_backend.services import provider_endpoint
from edcraft_backend.services.ai_authoring_providers import ProviderCredentials
from edcraft_backend.services.provider_endpoint import build_managed_provider


def test_managed_provider_guards_the_host_and_does_not_follow_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    guarded: list[str] = []

    class FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr(provider_endpoint, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(
        provider_endpoint.provider_host_guard,
        "assert_public_provider_host",
        lambda base_url: guarded.append(base_url),
    )
    credentials = ProviderCredentials(
        provider="openai",
        model="test-model",
        api_key="sk-test",
        base_url="https://api.example.com/v1",
    )

    provider = build_managed_provider(credentials)

    assert guarded == [credentials.base_url]
    http_client = captured["http_client"]
    assert http_client.follow_redirects is False
    http_client.close()
    provider.close()
    assert captured["closed"] is True


def test_endpoint_parse_applies_defaults_and_rejects_private_literals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert (
        provider_endpoint.ProviderEndpoint.parse("openai", None).base_url
        == "https://api.openai.com/v1"
    )

    monkeypatch.setenv("SOCLAAS_BASE_URL", " https://soclaas.example.com/v1 ")
    assert (
        provider_endpoint.ProviderEndpoint.parse("soclaas", None).base_url
        == "https://soclaas.example.com/v1"
    )

    with pytest.raises(provider_endpoint.ProviderConnectionInvalid):
        provider_endpoint.ProviderEndpoint.parse("openai", "https://10.0.0.5/v1")


async def test_list_models_rechecks_the_host_and_keeps_the_key_out_of_the_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guarded: list[str] = []
    captured: dict[str, str] = {}

    class FakeTransport:
        async def get(
            self, url: str, headers: dict[str, str], timeout: float
        ) -> provider_endpoint.ProviderHttpResponse:
            captured["url"] = url
            captured["authorization"] = headers["Authorization"]
            return provider_endpoint.ProviderHttpResponse(
                status_code=200,
                body=b'{"data": [{"id": "Alpha"}, {"id": "beta"}]}',
            )

    monkeypatch.setattr(
        provider_endpoint.provider_host_guard,
        "assert_public_provider_host",
        lambda base_url: guarded.append(base_url),
    )

    endpoint = provider_endpoint.ProviderEndpoint(
        kind="openai", base_url="https://host/v1"
    )
    assert await endpoint.list_models("sk-secret", transport=FakeTransport()) == [
        "Alpha",
        "beta",
    ]
    assert guarded == ["https://host/v1"]
    assert captured["url"] == "https://host/v1/models"
    assert "sk-secret" not in captured["url"]
    assert captured["authorization"] == "Bearer sk-secret"
