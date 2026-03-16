"""Association table for resource collaborators."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edcraft_backend.models.base import AssociationBase
from edcraft_backend.models.enums import CollaboratorRole, ResourceType

if TYPE_CHECKING:
    from edcraft_backend.models.user import User


class ResourceCollaborator(AssociationBase):
    """
    Generic collaborator table linking a user to a resource with a role.
    Uses a polymorphic resource_id (no FK) to support multiple resource types.
    """

    __tablename__ = "resource_collaborators"

    # Resource reference
    resource_type: Mapped[ResourceType] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(nullable=False)

    # User FK
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Role
    role: Mapped[CollaboratorRole] = mapped_column(String(50), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="resource_collaborations")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint(
            "resource_type", "resource_id", "user_id",
            name="uq_resource_collaborator",
        ),
        Index("ix_resource_collaborators_type_resource", "resource_type", "resource_id"),
        Index("ix_resource_collaborators_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ResourceCollaborator(resource_type={self.resource_type}, "
            f"resource_id={self.resource_id}, user_id={self.user_id}, role={self.role})>"
        )
