from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from edcraft_backend.exceptions import DuplicateResourceError, ResourceNotFoundError
from edcraft_backend.models.user import User
from edcraft_backend.repositories.user_repository import UserRepository
from edcraft_backend.schemas.user import UpdateUserRequest

if TYPE_CHECKING:
    from edcraft_backend.services.folder_service import FolderService


class UserService:
    """Service layer for User business logic."""

    def __init__(
        self,
        user_repository: UserRepository,
        folder_service: FolderService,
    ):
        self.user_repo = user_repository
        self.folder_svc = folder_service

    async def get_user(self, user_id: UUID) -> User:
        """Get a user by ID.

        Args:
            user_id: User UUID

        Returns:
            User entity

        Raises:
            ResourceNotFoundError: If user not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))
        return user

    async def update_user(self, user_id: UUID, user_data: UpdateUserRequest) -> User:
        """Update a user.

        Args:
            user_id: User UUID
            user_data: User update data

        Returns:
            Updated user

        Raises:
            ResourceNotFoundError: If user not found
            DuplicateResourceError: If email already taken
        """
        user = await self.get_user(user_id)

        update_data = user_data.model_dump(exclude_unset=True)

        # Check for email conflict if email is being updated
        if "email" in update_data and update_data["email"] != user.email:
            if await self.user_repo.email_exists(
                update_data["email"], exclude_id=user_id
            ):
                raise DuplicateResourceError("User", "email", update_data["email"])

        # Apply updates
        for key, value in update_data.items():
            setattr(user, key, value)

        return await self.user_repo.update(user)

    async def soft_delete_user(self, user_id: UUID) -> User:
        """Soft delete a user.

        Args:
            user_id: User UUID

        Returns:
            Soft-deleted user

        Raises:
            ResourceNotFoundError: If user not found
        """
        user = await self.get_user(user_id)

        root_folder = await self.folder_svc.get_root_folder(user_id)
        await self.folder_svc.soft_delete_folder(user_id, root_folder.id)

        return await self.user_repo.soft_delete(user)
