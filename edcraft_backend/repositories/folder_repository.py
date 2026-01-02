from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.folder import Folder
from edcraft_backend.repositories.base import EntityRepository


class FolderRepository(EntityRepository[Folder]):
    """Repository for Folder entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Folder, db)

    async def get_all_descendant_ids(
        self, folder_id: UUID, include_deleted: bool = False
    ) -> list[UUID]:
        """Get all descendant folder IDs using recursive CTE.

        Args:
            folder_id: Parent folder UUID
            include_deleted: Whether to include soft-deleted folders

        Returns:
            List of all descendant folder IDs (children, grandchildren, etc.)
        """
        # Build recursive CTE
        # NOTE: This is PostgreSQL-specific syntax
        if include_deleted:
            query = text(
                """
                WITH RECURSIVE descendants AS (
                    SELECT id, parent_id
                    FROM folders
                    WHERE parent_id = :folder_id

                    UNION ALL

                    SELECT f.id, f.parent_id
                    FROM folders f
                    INNER JOIN descendants d ON f.parent_id = d.id
                )
                SELECT id FROM descendants
            """
            )
        else:
            query = text(
                """
                WITH RECURSIVE descendants AS (
                    SELECT id, parent_id
                    FROM folders
                    WHERE parent_id = :folder_id AND deleted_at IS NULL

                    UNION ALL

                    SELECT f.id, f.parent_id
                    FROM folders f
                    INNER JOIN descendants d ON f.parent_id = d.id
                    WHERE f.deleted_at IS NULL
                )
                SELECT id FROM descendants
            """
            )

        result = await self.db.execute(query, {"folder_id": folder_id})
        return [row[0] for row in result]

    async def bulk_soft_delete_by_ids(self, folder_ids: list[UUID]) -> None:
        """Bulk soft-delete folders by IDs.

        Args:
            folder_ids: List of folder UUIDs to soft-delete
        """
        from datetime import UTC, datetime

        if not folder_ids:
            return

        stmt = (
            update(Folder)
            .where(Folder.id.in_(folder_ids))
            .where(Folder.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )

        await self.db.execute(stmt)
        await self.db.flush()

    async def get_root_folders(
        self,
        owner_id: UUID,
        include_deleted: bool = False,
    ) -> list[Folder]:
        """Get all root folders (no parent) for a user.

        Args:
            owner_id: User UUID
            include_deleted: Whether to include soft-deleted folders

        Returns:
            List of root folders
        """
        stmt = (
            select(Folder)
            .where(Folder.owner_id == owner_id, Folder.parent_id.is_(None))
            .order_by(Folder.name)
        )

        if not include_deleted:
            stmt = stmt.where(Folder.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_children(
        self,
        parent_id: UUID,
        include_deleted: bool = False,
    ) -> list[Folder]:
        """Get all direct children of a folder.

        Args:
            parent_id: Parent folder UUID
            include_deleted: Whether to include soft-deleted folders

        Returns:
            List of child folders
        """
        stmt = select(Folder).where(Folder.parent_id == parent_id).order_by(Folder.name)

        if not include_deleted:
            stmt = stmt.where(Folder.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def folder_name_exists(
        self,
        owner_id: UUID,
        name: str,
        parent_id: UUID | None = None,
        exclude_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> bool:
        """Check if a folder name already exists in the same parent.

        Args:
            owner_id: User UUID
            name: Folder name to check
            parent_id: Parent folder UUID (None for root folders)
            exclude_id: Optional folder ID to exclude from check (for updates)
            include_deleted: Whether to include soft-deleted folders

        Returns:
            True if name exists, False otherwise
        """
        stmt = select(Folder).where(
            Folder.owner_id == owner_id,
            Folder.name == name,
        )

        if parent_id is None:
            stmt = stmt.where(Folder.parent_id.is_(None))
        else:
            stmt = stmt.where(Folder.parent_id == parent_id)

        if exclude_id:
            stmt = stmt.where(Folder.id != exclude_id)

        if not include_deleted:
            stmt = stmt.where(Folder.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
