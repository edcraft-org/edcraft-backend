"""User endpoints."""

from fastapi import APIRouter, HTTPException, status

from edcraft_backend.dependencies import (
    CurrentUserDep,
    FolderServiceDep,
    UserServiceDep,
)
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.folder import Folder
from edcraft_backend.models.user import User
from edcraft_backend.schemas.folder import FolderResponse
from edcraft_backend.schemas.user import (
    UpdateUserRequest,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_user(user: CurrentUserDep, service: UserServiceDep) -> User:
    """Get the current authenticated user."""
    try:
        return await service.get_user(user.id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/me", response_model=UserResponse)
async def update_user(
    user: CurrentUserDep, user_data: UpdateUserRequest, service: UserServiceDep
) -> User:
    """Update the current authenticated user."""
    try:
        return await service.update_user(user.id, user_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_user(user: CurrentUserDep, service: UserServiceDep) -> None:
    """Soft delete the current authenticated user."""
    try:
        await service.soft_delete_user(user.id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/me/root-folder", response_model=FolderResponse)
async def get_user_root_folder(
    user: CurrentUserDep,
    user_service: UserServiceDep,
    folder_service: FolderServiceDep,
) -> Folder:
    """Get the root folder for the current authenticated user."""
    try:
        await user_service.get_user(user.id)
        return await folder_service.get_root_folder(user.id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
