"""User endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from edcraft_backend.dependencies import UserServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.user import User
from edcraft_backend.schemas.user import UserCreate, UserList, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, service: UserServiceDep) -> User:
    """Create a new user."""
    try:
        return await service.create_user(user_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("", response_model=list[UserList])
async def list_users(service: UserServiceDep) -> list[User]:
    """List all users (excluding soft-deleted)."""
    try:
        return await service.list_users()
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, service: UserServiceDep) -> User:
    """Get a user by ID."""
    try:
        return await service.get_user(user_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, user_data: UserUpdate, service: UserServiceDep
) -> User:
    """Update a user."""
    try:
        return await service.update_user(user_id, user_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_user(user_id: UUID, service: UserServiceDep) -> None:
    """Soft delete a user."""
    try:
        await service.soft_delete_user(user_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{user_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_user(user_id: UUID, service: UserServiceDep) -> None:
    """Hard delete a user (cascade deletes all content)."""
    try:
        await service.hard_delete_user(user_id)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
