"""Owner-scoped BYOK provider connection endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, status

from edcraft_backend.dependencies import (
    CurrentUserDep,
    ProviderConnectionServiceDep,
)
from edcraft_backend.schemas.ai_authoring import ErrorResponse
from edcraft_backend.schemas.provider_connection import (
    ProviderConnectionCreate,
    ProviderConnectionResponse,
    ProviderConnectionUpdate,
    ProviderModelList,
    ProviderProbeRequest,
)

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not signed in."},
    404: {"model": ErrorResponse, "description": "Unknown or unowned connection."},
    422: {"model": ErrorResponse, "description": "Invalid connection settings."},
    502: {"model": ErrorResponse, "description": "Provider probe failed."},
}

router = APIRouter(
    prefix="/ai-authoring/connections",
    tags=["ai-authoring"],
    responses=_ERROR_RESPONSES,
)


@router.get("", response_model=list[ProviderConnectionResponse])
async def list_connections(
    user: CurrentUserDep,
    service: ProviderConnectionServiceDep,
) -> list[ProviderConnectionResponse]:
    """List the caller's provider connections without exposing secrets."""
    return await service.list_connections(user.id)


@router.post(
    "",
    response_model=ProviderConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    payload: ProviderConnectionCreate,
    user: CurrentUserDep,
    service: ProviderConnectionServiceDep,
) -> ProviderConnectionResponse:
    """Store one encrypted provider connection for the caller."""
    return await service.create(user.id, payload)


@router.post("/probe", response_model=ProviderModelList)
async def probe_connection(
    payload: ProviderProbeRequest,
    user: CurrentUserDep,
    service: ProviderConnectionServiceDep,
) -> ProviderModelList:
    """Test credentials before saving them and list available models."""
    return await service.probe(payload)


@router.patch("/{connection_id}", response_model=ProviderConnectionResponse)
async def update_connection(
    connection_id: UUID,
    payload: ProviderConnectionUpdate,
    user: CurrentUserDep,
    service: ProviderConnectionServiceDep,
) -> ProviderConnectionResponse:
    """Update metadata or rotate the key without returning it."""
    return await service.update(user.id, connection_id, payload)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: UUID,
    user: CurrentUserDep,
    service: ProviderConnectionServiceDep,
) -> None:
    """Forget a connection; existing jobs keep their non-secret snapshot."""
    await service.delete(user.id, connection_id)


@router.post("/{connection_id}/test", response_model=ProviderModelList)
async def test_connection(
    connection_id: UUID,
    user: CurrentUserDep,
    service: ProviderConnectionServiceDep,
) -> ProviderModelList:
    """Re-test a stored connection and refresh its cached model list."""
    return await service.verify(user.id, connection_id)
