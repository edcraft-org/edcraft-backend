"""CRUD, probing, and credential resolution for provider connections."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from pydantic import SecretStr

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
from edcraft_backend.services.provider_endpoint import (
    MAX_MODELS,
    ProviderEndpoint,
    ResolvedConnection,
)
from edcraft_backend.services.provider_errors import (
    ProviderConnectionInvalid,
    ProviderConnectionNotFound,
)
from edcraft_backend.services.provider_secrets import ProviderSecretCipher


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
        base_url = ProviderEndpoint.parse(request.kind, request.base_url).base_url
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
            base_url = ProviderEndpoint.parse(
                cast(ProviderKind, connection.kind), request.base_url
            ).base_url
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
        endpoint = ProviderEndpoint.parse(request.kind, request.base_url)
        models = await endpoint.list_models(api_key)
        return ProviderModelList(
            models=models,
            default_model=models[0] if models else None,
        )

    async def verify(self, owner_id: UUID, connection_id: UUID) -> ProviderModelList:
        """Re-test a stored connection and cache the discovered models."""
        connection = await self._owned(owner_id, connection_id)
        api_key = self._decrypt(connection)
        endpoint = ProviderEndpoint.parse(
            cast(ProviderKind, connection.kind), connection.base_url
        )
        models = await endpoint.list_models(api_key)
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
    ) -> ResolvedConnection:
        """Decrypt one connection for a single job, never persisting the key."""
        connection = await self._owned(owner_id, connection_id)
        if not connection.enabled:
            raise ProviderConnectionInvalid("This model connection is disabled.")
        selected = _normalize_model(model or connection.default_model)
        if connection.models and selected not in connection.models:
            raise ProviderConnectionInvalid("Choose a model that belongs to this connection.")
        endpoint = ProviderEndpoint.parse(
            cast(ProviderKind, connection.kind), connection.base_url
        )
        return ResolvedConnection.for_connection(
            connection_id=connection.id,
            provider=connection.kind,
            model=selected,
            api_key=self._decrypt(connection),
            base_url=endpoint.base_url,
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
