from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Mapped


@runtime_checkable
class OrderableEntity(Protocol):
    """Structural type for entities that support ordering."""

    id: Mapped
    order: Mapped[int | None]
