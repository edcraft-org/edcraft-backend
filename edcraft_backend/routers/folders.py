"""Folder endpoints with tree operations."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from edcraft_backend.dependencies import CurrentUserDep, FolderServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.folder import Folder
from edcraft_backend.schemas.folder import (
    CreateFolderRequest,
    FolderPathResponse,
    FolderResponse,
    FolderTreeResponse,
    FolderWithContentsResponse,
    MoveFolderRequest,
    UpdateFolderRequest,
)

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    current_user: CurrentUserDep,
    folder_data: CreateFolderRequest,
    service: FolderServiceDep,
) -> Folder:
    """Create a new folder."""
    try:
        return await service.create_folder(current_user.id, folder_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("", response_model=list[FolderResponse])
async def list_folders(
    current_user: CurrentUserDep,
    service: FolderServiceDep,
    parent_id: UUID | None = Query(None, description="Parent ID to filter by"),
) -> list[Folder]:
    """List folders for a user, filtered by parent."""
    try:
        return await service.list_folders(current_user.id, parent_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    current_user: CurrentUserDep, folder_id: UUID, service: FolderServiceDep
) -> Folder:
    """Get a folder by ID."""
    try:
        return await service.get_folder(current_user.id, folder_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{folder_id}/contents", response_model=FolderWithContentsResponse)
async def get_folder_contents(
    current_user: CurrentUserDep, folder_id: UUID, service: FolderServiceDep
) -> FolderWithContentsResponse:
    """Get folder with complete contents (assessments and templates)."""
    try:
        return await service.get_folder_with_contents(current_user.id, folder_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{folder_id}/tree", response_model=FolderTreeResponse)
async def get_folder_tree(
    current_user: CurrentUserDep, folder_id: UUID, service: FolderServiceDep
) -> FolderTreeResponse:
    """Get folder with full subtree (all descendants in nested structure)."""
    try:
        return await service.get_folder_tree(current_user.id, folder_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{folder_id}/path", response_model=FolderPathResponse)
async def get_folder_path(
    current_user: CurrentUserDep, folder_id: UUID, service: FolderServiceDep
) -> dict[str, list[Folder]]:
    """Get folder path from root to current folder."""
    try:
        path = await service.get_folder_path(current_user.id, folder_id)
        return {"path": path}
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    current_user: CurrentUserDep,
    folder_id: UUID,
    folder_data: UpdateFolderRequest,
    service: FolderServiceDep,
) -> Folder:
    """Update folder (name, description)."""
    try:
        return await service.update_folder(current_user.id, folder_id, folder_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{folder_id}/move", response_model=FolderResponse)
async def move_folder(
    current_user: CurrentUserDep,
    folder_id: UUID,
    move_data: MoveFolderRequest,
    service: FolderServiceDep,
) -> Folder:
    """Move folder to different parent."""
    try:
        return await service.move_folder(current_user.id, folder_id, move_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_folder(
    current_user: CurrentUserDep,
    folder_id: UUID,
    service: FolderServiceDep,
) -> None:
    """Soft delete folder (cascade to children) and clean up orphaned resources."""
    try:
        await service.soft_delete_non_root_folder(current_user.id, folder_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
