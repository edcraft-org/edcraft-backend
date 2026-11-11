"""User-owned model provider connections (BYOK)."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import EntityBase

if TYPE_CHECKING:
    from edcraft_backend.models.user import User


class ProviderConnection(EntityBase):
    """One encrypted provider credential owned by a signed-in user."""

    __tablename__ = "provider_connections"

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_last4: Mapped[str] = mapped_column(String(8), nullable=False)
    default_model: Mapped[str] = mapped_column(String(120), nullable=False)
    models: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship()

    __table_args__ = (Index("ix_provider_connections_owner_name", "owner_id", "name"),)

    def __repr__(self) -> str:
        return f"<ProviderConnection(id={self.id}, kind={self.kind}, owner_id={self.owner_id})>"
