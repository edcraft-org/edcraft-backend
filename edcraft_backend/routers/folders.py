"""Folder endpoints with tree operations."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from edcraft_backend.dependencies import FolderServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.folder import Folder
from edcraft_backend.schemas.folder import (
    FolderCreate,
    FolderMove,
    FolderPath,
    FolderResponse,
    FolderTree,
    FolderUpdate,
    FolderWithContents,
)

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(folder_data: FolderCreate, service: FolderServiceDep) -> Folder:
    """Create a new folder."""
    try:
        return await service.create_folder(folder_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("", response_model=list[FolderResponse])
async def list_folders(
    service: FolderServiceDep,
    owner_id: UUID = Query(..., description="Owner ID to filter folders"),
    parent_id: UUID | None = Query(None, description="Parent ID to filter by"),
) -> list[Folder]:
    """List folders for a user, filtered by parent."""
    try:
        return await service.list_folders(owner_id, parent_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(folder_id: UUID, service: FolderServiceDep) -> Folder:
    """Get a folder by ID."""
    try:
        return await service.get_folder(folder_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{folder_id}/contents", response_model=FolderWithContents)
async def get_folder_contents(
    folder_id: UUID, service: FolderServiceDep
) -> FolderWithContents:
    """Get folder with complete contents (assessments and templates)."""
    try:
        return await service.get_folder_with_contents(folder_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{folder_id}/tree", response_model=FolderTree)
async def get_folder_tree(folder_id: UUID, service: FolderServiceDep) -> FolderTree:
    """Get folder with full subtree (all descendants in nested structure)."""
    try:
        return await service.get_folder_tree(folder_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{folder_id}/path", response_model=FolderPath)
async def get_folder_path(
    folder_id: UUID, service: FolderServiceDep
) -> dict[str, list[Folder]]:
    """Get folder path from root to current folder."""
    try:
        path = await service.get_folder_path(folder_id)
        return {"path": path}
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: UUID, folder_data: FolderUpdate, service: FolderServiceDep
) -> Folder:
    """Update folder (name, description)."""
    try:
        return await service.update_folder(folder_id, folder_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{folder_id}/move", response_model=FolderResponse)
async def move_folder(
    folder_id: UUID, move_data: FolderMove, service: FolderServiceDep
) -> Folder:
    """Move folder to different parent."""
    try:
        return await service.move_folder(folder_id, move_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_folder(folder_id: UUID, service: FolderServiceDep) -> None:
    """Soft delete folder (cascade to children)."""
    try:
        await service.soft_delete_folder(folder_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
