from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from edcraft_backend.repositories.mixins.types import OrderableEntity


class OrderableRepositoryMixin[T: OrderableEntity]:
    """Mixin for entities ordered within a parent container."""

    model: type[T]
    db: AsyncSession

    def _parent_filter(self, parent_id: Any) -> ColumnElement[bool]:
        raise NotImplementedError

    def _base_filters(self) -> tuple[ColumnElement[bool], ...]:
        return ()

    async def shift_orders_from(self, parent_id: Any, start_order: int) -> None:
        stmt = (
            update(self.model)
            .where(
                self._parent_filter(parent_id),
                self.model.order >= start_order,
                *self._base_filters(),
            )
            .values(order=self.model.order + 1)
        )

        await self.db.execute(stmt)
        await self.db.flush()

    async def normalize_orders(self, parent_id: Any) -> None:
        subq = (
            select(
                self.model.id,
                (func.row_number().over(order_by=self.model.order) - 1).label(
                    "new_order"
                ),
            )
            .where(
                self._parent_filter(parent_id),
                *self._base_filters(),
            )
            .subquery()
        )

        stmt = (
            update(self.model)
            .where(self.model.id == subq.c.id)
            .values(order=subq.c.new_order)
        )

        await self.db.execute(stmt)
        await self.db.flush()
