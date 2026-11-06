"""Provider construction guards for user-supplied base URLs."""

from __future__ import annotations

from typing import Any

import pytest

from edcraft_backend.services import ai_authoring_providers
from edcraft_backend.services.ai_authoring_providers import (
    ProviderCredentials,
    build_managed_provider,
)


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

    monkeypatch.setattr(ai_authoring_providers, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(
        "edcraft_backend.services.provider_connection_service._assert_public_provider_host",
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
