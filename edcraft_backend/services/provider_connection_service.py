"""CRUD, probing, and credential resolution for provider connections."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
from datetime import UTC, datetime
from typing import cast
from urllib.parse import urlparse, urlsplit, urlunsplit
from uuid import UUID

import httpx
from pydantic import SecretStr

from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.provider_connection import ProviderConnection
from edcraft_backend.repositories.provider_connection_repository import (
    ProviderConnectionRepository,
)
from edcraft_backend.schemas.provider_connection import (
    ProviderConnectionCreate,
    ProviderConnectionResponse,
    ProviderConnectionUpdate,
    ProviderKind,
    ProviderModelList,
    ProviderProbeRequest,
)
from edcraft_backend.services.ai_authoring_providers import ProviderCredentials
from edcraft_backend.services.provider_secrets import ProviderSecretCipher

DEFAULT_BASE_URLS: dict[ProviderKind, str | None] = {
    "soclaas": None,
    "openai": "https://api.openai.com/v1",
}
BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata",
    "instance-data",
}
MAX_MODELS = 500
PROBE_TIMEOUT_SECONDS = 20.0


class ProviderConnectionError(EdCraftBaseException):
    """Base class for sanitized provider-connection errors."""


class ProviderConnectionNotFound(ProviderConnectionError):
    """The connection is unknown or owned by another user."""

    def __init__(self, message: str = "Model connection not found.") -> None:
        super().__init__(message, 404)


class ProviderConnectionInvalid(ProviderConnectionError):
    """The supplied connection settings cannot be used."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 422)


class ProviderConnectionUnavailable(ProviderConnectionError):
    """The provider could not be contacted or rejected the key."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 502)


class ProviderConnectionService:
    """Own connection persistence, secret handling, and provider probing."""

    def __init__(
        self,
        repository: ProviderConnectionRepository,
        cipher: ProviderSecretCipher,
    ) -> None:
        self._repository = repository
        self._cipher = cipher

    async def list_connections(self, owner_id: UUID) -> list[ProviderConnectionResponse]:
        connections = await self._repository.list_for_owner(owner_id, include_disabled=True)
        return [self._view(connection) for connection in connections]

    async def create(
        self, owner_id: UUID, request: ProviderConnectionCreate
    ) -> ProviderConnectionResponse:
        api_key = _secret_value(request.api_key, "API key")
        base_url = _effective_base_url(request.kind, request.base_url)
        models = _normalize_models(request.models)
        default_model = _normalize_model(request.default_model)

        connection = ProviderConnection(
            owner_id=owner_id,
            name=request.name.strip(),
            kind=request.kind,
            base_url=base_url,
            api_key_ciphertext=self._cipher.encrypt(api_key),
            api_key_last4=_last_four(api_key),
            default_model=default_model,
            models=_include_default_model(models, default_model),
            enabled=True,
        )
        created = await self._repository.create(connection)
        return self._view(created)

    async def update(
        self,
        owner_id: UUID,
        connection_id: UUID,
        request: ProviderConnectionUpdate,
    ) -> ProviderConnectionResponse:
        connection = await self._owned(owner_id, connection_id)
        supplied = request.model_fields_set

        if "name" in supplied and request.name is not None:
            connection.name = request.name.strip()
        if "base_url" in supplied:
            base_url = _effective_base_url(cast(ProviderKind, connection.kind), request.base_url)
            if base_url != connection.base_url:
                connection.base_url = base_url
                connection.verified_at = None
        if "api_key" in supplied and request.api_key is not None:
            api_key = _secret_value(request.api_key, "API key")
            connection.api_key_ciphertext = self._cipher.encrypt(api_key)
            connection.api_key_last4 = _last_four(api_key)
            connection.verified_at = None
        if "default_model" in supplied and request.default_model is not None:
            connection.default_model = _normalize_model(request.default_model)
        if "models" in supplied and request.models is not None:
            connection.models = _normalize_models(request.models)
        if "enabled" in supplied and request.enabled is not None:
            connection.enabled = request.enabled

        connection.models = _include_default_model(
            list(connection.models or []), connection.default_model
        )
        updated = await self._repository.update(connection)
        return self._view(updated)

    async def delete(self, owner_id: UUID, connection_id: UUID) -> None:
        connection = await self._owned(owner_id, connection_id)
        await self._repository.hard_delete(connection)

    async def probe(self, request: ProviderProbeRequest) -> ProviderModelList:
        """Test unsaved credentials and return the provider's model list."""
        api_key = _secret_value(request.api_key, "API key")
        base_url = _effective_base_url(request.kind, request.base_url)
        models = await self._list_models(base_url, api_key)
        return ProviderModelList(
            models=models,
            default_model=models[0] if models else None,
        )

    async def verify(self, owner_id: UUID, connection_id: UUID) -> ProviderModelList:
        """Re-test a stored connection and cache the discovered models."""
        connection = await self._owned(owner_id, connection_id)
        api_key = self._decrypt(connection)
        base_url = _effective_base_url(cast(ProviderKind, connection.kind), connection.base_url)
        models = await self._list_models(base_url, api_key)
        connection.models = models
        connection.verified_at = datetime.now(UTC)
        if models and connection.default_model not in models:
            connection.default_model = models[0]
        await self._repository.update(connection)
        return ProviderModelList(
            models=models,
            default_model=connection.default_model if models else None,
        )

    async def resolve(
        self,
        owner_id: UUID,
        connection_id: UUID,
        model: str | None,
    ) -> ProviderCredentials:
        """Decrypt one connection for a single job, never persisting the key."""
        connection = await self._owned(owner_id, connection_id)
        if not connection.enabled:
            raise ProviderConnectionInvalid("This model connection is disabled.")
        selected = _normalize_model(model or connection.default_model)
        if connection.models and selected not in connection.models:
            raise ProviderConnectionInvalid("Choose a model that belongs to this connection.")
        return ProviderCredentials(
            provider=connection.kind,
            model=selected,
            api_key=self._decrypt(connection),
            base_url=_effective_base_url(cast(ProviderKind, connection.kind), connection.base_url),
        )

    async def _owned(self, owner_id: UUID, connection_id: UUID) -> ProviderConnection:
        connection = await self._repository.get_owned(connection_id, owner_id)
        if connection is None:
            raise ProviderConnectionNotFound()
        return connection

    def _decrypt(self, connection: ProviderConnection) -> str:
        try:
            return self._cipher.decrypt(connection.api_key_ciphertext)
        except Exception as exc:  # ProviderSecretError is intentionally sanitized
            raise ProviderConnectionInvalid(str(exc)) from exc

    @staticmethod
    def _view(connection: ProviderConnection) -> ProviderConnectionResponse:
        return ProviderConnectionResponse(
            id=connection.id,
            name=connection.name,
            kind=cast(ProviderKind, connection.kind),
            base_url=connection.base_url,
            default_model=connection.default_model,
            models=list(connection.models or []),
            enabled=connection.enabled,
            key_last4=connection.api_key_last4,
            verified_at=connection.verified_at,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )

    @staticmethod
    async def _list_models(base_url: str, api_key: str) -> list[str]:
        payload = await _fetch_models_payload(base_url, api_key)
        entries = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise ProviderConnectionUnavailable(
                "The provider's model list was not in the expected format."
            )
        return _extract_model_ids(entries)


async def _fetch_models_payload(base_url: str, api_key: str) -> object:
    """Fetch a provider's model list, translating failures to safe errors."""
    try:
        # Resolve immediately before the request so a hostname cannot be
        # rebound to a private address between validation and use.
        await asyncio.to_thread(_assert_public_provider_host, base_url)
        url = _models_url(base_url)
        async with httpx.AsyncClient(
            timeout=PROBE_TIMEOUT_SECONDS, follow_redirects=False
        ) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
    except (httpx.InvalidURL, ValueError) as exc:
        raise ProviderConnectionInvalid("The provider base URL is not a valid HTTP URL.") from exc
    except httpx.RequestError as exc:
        raise ProviderConnectionUnavailable(
            "Could not reach the provider. Check the base URL and network access."
        ) from exc

    _raise_for_model_response(response)
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderConnectionUnavailable(
            "The provider's model list was not valid JSON."
        ) from exc


def _models_url(base_url: str) -> str:
    """Join the models path onto the base path without string concatenation."""
    parts = urlsplit(base_url)
    path = f"{parts.path.rstrip('/')}/models"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _raise_for_model_response(response: httpx.Response) -> None:
    if response.status_code in {401, 403}:
        raise ProviderConnectionUnavailable("The provider rejected this API key.")
    if response.status_code == 404:
        raise ProviderConnectionUnavailable(
            "The provider's model list was not found. Check the base URL."
        )
    if response.status_code >= 400:
        raise ProviderConnectionUnavailable(
            f"The provider returned HTTP {response.status_code} while listing models."
        )


def _extract_model_ids(entries: list[object]) -> list[str]:
    models: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("id")
        if not isinstance(model_id, str):
            continue
        candidate = model_id.strip()
        if not candidate or len(candidate) > 120 or candidate in seen:
            continue
        seen.add(candidate)
        models.append(candidate)
    return sorted(models, key=str.lower)[:MAX_MODELS]


def _secret_value(secret: SecretStr, label: str) -> str:
    value = secret.get_secret_value().strip()
    if not value:
        raise ProviderConnectionInvalid(f"{label} must not be blank.")
    if len(value) > 4096:
        raise ProviderConnectionInvalid(f"{label} is too long.")
    return value


def _normalize_model(value: str) -> str:
    model = value.strip()
    if not model:
        raise ProviderConnectionInvalid("Choose a model.")
    if len(model) > 120:
        raise ProviderConnectionInvalid("Model names must be 120 characters or fewer.")
    return model


def _normalize_models(values: list[str]) -> list[str]:
    models: list[str] = []
    seen: set[str] = set()
    for value in values:
        model = value.strip()
        if not model or len(model) > 120 or model in seen:
            continue
        seen.add(model)
        models.append(model)
    return models[:MAX_MODELS]


def _include_default_model(models: list[str], default_model: str) -> list[str]:
    """Keep the selected default valid even after editing a model list."""
    if models and default_model not in models:
        return [*models, default_model]
    return models


def _last_four(api_key: str) -> str:
    return api_key[-4:] if len(api_key) >= 4 else "****"


def _effective_base_url(kind: ProviderKind, raw: str | None) -> str:
    """Validate a provider URL and apply the kind's default when omitted."""
    value = _resolve_base_url(kind, raw)
    if len(value) > 500:
        raise ProviderConnectionInvalid("Base URL must be 500 characters or fewer.")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        raise ProviderConnectionInvalid("Base URL must not contain control characters.")

    try:
        parsed = urlparse(value)
        # Accessing .port validates malformed and out-of-range port values.
        _ = parsed.port
    except ValueError as exc:
        raise ProviderConnectionInvalid("Base URL has an invalid host or port.") from exc

    if parsed.query or parsed.fragment:
        raise ProviderConnectionInvalid(
            "Base URL must not include a query string or fragment; remove the '?' and '#' portions."
        )
    if parsed.scheme not in {"http", "https"}:
        raise ProviderConnectionInvalid("Base URL must use http or https.")
    if parsed.username or parsed.password:
        raise ProviderConnectionInvalid("Base URL must not contain credentials.")
    hostname = parsed.hostname
    if not hostname:
        raise ProviderConnectionInvalid("Base URL must include a host.")
    if any(char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F for char in hostname):
        raise ProviderConnectionInvalid("Base URL host must not contain whitespace or controls.")
    hostname = hostname.removesuffix(".")
    if parsed.scheme == "http" and not _is_loopback(hostname):
        raise ProviderConnectionInvalid(
            "Use HTTPS for remote providers; HTTP is allowed only for localhost."
        )
    _reject_unsafe_host(hostname)
    return value.rstrip("/")


def _resolve_base_url(kind: ProviderKind, raw: str | None) -> str:
    value = (raw or "").strip()
    if not value and kind == "soclaas":
        value = os.getenv("SOCLAAS_BASE_URL", "").strip()
    if not value:
        value = DEFAULT_BASE_URLS[kind] or ""
    if not value:
        raise ProviderConnectionInvalid("Enter the SocLaas base URL (for example https://host/v1).")
    return value


def _allow_private_provider_hosts() -> bool:
    """Development-only escape hatch; disabled unless explicitly enabled."""
    value = os.getenv("PROVIDER_ALLOW_PRIVATE_HOSTS", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _reject_unsafe_host(hostname: str) -> None:
    host = hostname.removesuffix(".").lower()
    if host in BLOCKED_HOSTNAMES:
        raise ProviderConnectionInvalid("This provider host is not allowed.")
    if host == "localhost" or host.endswith(".localhost"):
        if not _allow_private_provider_hosts():
            raise ProviderConnectionInvalid(
                "This provider address is not allowed. Use a public host, or set "
                "PROVIDER_ALLOW_PRIVATE_HOSTS=true only for local development."
            )
        return
    address = _parse_ip(host)
    if address is None:
        return
    _reject_unsafe_address(address)


def _reject_unsafe_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    # These ranges are never valid provider destinations, even in development.
    if address.is_link_local or address.is_multicast or address.is_unspecified:
        raise ProviderConnectionInvalid("This provider address is not allowed.")
    if getattr(address, "is_shared", False):
        raise ProviderConnectionInvalid("This provider address is not allowed.")
    if _allow_private_provider_hosts():
        if address.is_loopback or (address.is_private and not address.is_reserved):
            return
        raise ProviderConnectionInvalid("This provider address is not allowed.")
    if address.is_global:
        return
    raise ProviderConnectionInvalid(
        "This provider address is not allowed. Use a public host, or set "
        "PROVIDER_ALLOW_PRIVATE_HOSTS=true only for local development."
    )


def _assert_public_provider_host(base_url: str) -> None:
    """Reject a hostname that resolves to a non-public address.

    Resolution failures are left to the HTTP request so they surface as the
    existing sanitized 502 instead of a validation error.
    """
    try:
        parts = urlsplit(base_url)
        hostname = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise ProviderConnectionInvalid("Base URL has an invalid host or port.") from exc
    if not hostname:
        raise ProviderConnectionInvalid("Base URL must include a host.")
    host = hostname.removesuffix(".").lower()
    _reject_unsafe_host(host)
    resolved_port = port or (443 if parts.scheme == "https" else 80)
    try:
        results = socket.getaddrinfo(host, resolved_port, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError):
        return
    for _family, _type, _proto, _canonname, sockaddr in results:
        address = _parse_ip(str(sockaddr[0]))
        if address is not None:
            _reject_unsafe_address(address)


def _is_loopback(hostname: str) -> bool:
    host = hostname.removesuffix(".").lower()
    if host == "localhost":
        return True
    address = _parse_ip(host)
    return address is not None and address.is_loopback


def _parse_ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None
