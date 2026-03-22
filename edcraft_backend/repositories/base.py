"""Base repository classes for entities and associations."""

from edcraft_backend.repositories.association_repository import AssociationRepository
from edcraft_backend.repositories.collaborative_resource_repository import (
    FolderResourceRepository,
)
from edcraft_backend.repositories.entity_repository import EntityRepository

__all__ = ["EntityRepository", "AssociationRepository", "FolderResourceRepository"]
