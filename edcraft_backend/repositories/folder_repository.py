from uuid import UUID

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from edcraft_backend.models.folder import Folder
from edcraft_backend.repositories.base import EntityRepository


class FolderRepository(EntityRepository[Folder]):
    """Repository for Folder entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Folder, db)

    async def get_all_descendant_ids(
        self, folder_id: UUID, include_deleted: bool = False
    ) -> list[UUID]:
        base_query = select(Folder.id, Folder.parent_id).where(
            Folder.parent_id == folder_id
        )

        if not include_deleted:
            base_query = base_query.where(Folder.deleted_at.is_(None))

        descendants_cte = base_query.cte(name="descendants", recursive=True)

        folder_alias = aliased(Folder)

        recursive_query = select(folder_alias.id, folder_alias.parent_id).join(
            descendants_cte, folder_alias.parent_id == descendants_cte.c.id
        )

        if not include_deleted:
            recursive_query = recursive_query.where(folder_alias.deleted_at.is_(None))

        descendants_cte = descendants_cte.union_all(recursive_query)

        stmt = select(descendants_cte.c.id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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

    async def get_root_folder(
        self,
        owner_id: UUID,
        include_deleted: bool = False,
    ) -> Folder:
        """Get the root folder for a user.

        Args:
            owner_id: User UUID
            include_deleted: Whether to include soft-deleted folders

        Returns:
            Root folder

        Note:
            Root folders are created during user registration and protected from deletion.
            This should never return None for valid users.
        """
        stmt = select(Folder).where(
            Folder.owner_id == owner_id, Folder.parent_id.is_(None)
        )

        if not include_deleted:
            stmt = stmt.where(Folder.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one()

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
        conditions = [
            Folder.owner_id == owner_id,
            Folder.name == name,
        ]

        if parent_id is None:
            conditions.append(Folder.parent_id.is_(None))
        else:
            conditions.append(Folder.parent_id == parent_id)

        if exclude_id is not None:
            conditions.append(Folder.id != exclude_id)

        if not include_deleted:
            conditions.append(Folder.deleted_at.is_(None))

        stmt = select(exists().where(*conditions))

        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def is_ancestor(self, potential_ancestor_id: UUID, folder_id: UUID) -> bool:
        base_query = select(Folder.id, Folder.parent_id).where(
            Folder.id == folder_id,
            Folder.deleted_at.is_(None),
        )

        ancestors_cte = base_query.cte(name="ancestors", recursive=True)

        folder_alias = aliased(Folder)

        recursive_query = (
            select(folder_alias.id, folder_alias.parent_id)
            .join(ancestors_cte, folder_alias.id == ancestors_cte.c.parent_id)
            .where(folder_alias.deleted_at.is_(None))
        )

        ancestors_cte = ancestors_cte.union_all(recursive_query)

        stmt = select(ancestors_cte.c.id).where(
            ancestors_cte.c.id == potential_ancestor_id
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
