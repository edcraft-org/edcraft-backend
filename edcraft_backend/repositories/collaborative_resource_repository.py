"""Base repository for folder resource entities."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.base import FolderResourceBase
from edcraft_backend.models.enums import CollaboratorRole, ResourceType
from edcraft_backend.models.resource_collaborator import ResourceCollaborator
from edcraft_backend.repositories.entity_repository import EntityRepository


class FolderResourceRepository[ModelType: FolderResourceBase](
    EntityRepository[ModelType]
):
    """Repository for resource entities that support folders and collaboration."""

    def __init__(
        self, model: type[ModelType], resource_type: ResourceType, db: AsyncSession
    ):
        super().__init__(model, db)
        self.resource_type = resource_type

    async def get_by_folder(
        self,
        folder_id: UUID,
        include_deleted: bool = False,
    ) -> list[ModelType]:
        """Get all resources in a folder, ordered by last updated descending."""
        stmt = (
            select(self.model)
            .where(self.model.folder_id == folder_id)
            .order_by(self.model.updated_at.desc())
        )
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_collaborator(
        self,
        user_id: UUID,
        collab_filter: Literal["all", "owned", "shared"] = "all",
        folder_id: UUID | None = None,
    ) -> list[tuple[ModelType, CollaboratorRole]]:
        """List resources the user has access to via the collaborator table."""
        stmt = (
            select(self.model, ResourceCollaborator.role)
            .join(
                ResourceCollaborator,
                (ResourceCollaborator.resource_id == self.model.id)
                & (ResourceCollaborator.resource_type == self.resource_type),
            )
            .where(
                self.model.deleted_at.is_(None),
                ResourceCollaborator.user_id == user_id,
            )
        )
        if collab_filter == "owned":
            stmt = stmt.where(ResourceCollaborator.role == CollaboratorRole.OWNER)
        elif collab_filter == "shared":
            stmt = stmt.where(ResourceCollaborator.role != CollaboratorRole.OWNER)
        if folder_id is not None:
            stmt = stmt.where(self.model.folder_id == folder_id)
        stmt = stmt.order_by(self.model.updated_at.desc())
        result = await self.db.execute(stmt)
        return [(row[0], CollaboratorRole(row[1])) for row in result.all()]

    async def bulk_soft_delete_by_folder_ids(self, folder_ids: list[UUID]) -> None:
        """Bulk soft-delete resources belonging to the given folder IDs."""
        if not folder_ids:
            return
        stmt = (
            update(self.model)
            .where(self.model.folder_id.in_(folder_ids))
            .where(self.model.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.flush()
