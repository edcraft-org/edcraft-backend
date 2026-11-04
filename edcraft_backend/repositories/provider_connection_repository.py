"""Owner-scoped persistence for provider connections."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.provider_connection import ProviderConnection
from edcraft_backend.repositories.entity_repository import EntityRepository


class ProviderConnectionRepository(EntityRepository[ProviderConnection]):
    """Query provider connections only through their owner boundary."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ProviderConnection, db)

    async def list_for_owner(
        self, owner_id: UUID, *, include_disabled: bool = False
    ) -> list[ProviderConnection]:
        stmt = (
            select(ProviderConnection)
            .where(
                ProviderConnection.owner_id == owner_id,
                ProviderConnection.deleted_at.is_(None),
            )
            .order_by(ProviderConnection.name, ProviderConnection.created_at)
        )
        if not include_disabled:
            stmt = stmt.where(ProviderConnection.enabled.is_(True))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_owned(self, connection_id: UUID, owner_id: UUID) -> ProviderConnection | None:
        result = await self.db.execute(
            select(ProviderConnection).where(
                ProviderConnection.id == connection_id,
                ProviderConnection.owner_id == owner_id,
                ProviderConnection.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
