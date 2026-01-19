"""make folder_id required for assessments and templates

Revision ID: 20260119_make_folder_required
Revises: 20260119_add_root_folders
Create Date: 2026-01-19

"""

from collections.abc import Sequence

from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260119_make_folder_required"
down_revision: str | Sequence[str] | None = "20260119_add_root_folders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make folder_id NOT NULL in assessments and assessment_templates."""
    # Alter assessments.folder_id to NOT NULL
    op.alter_column(
        "assessments",
        "folder_id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )

    # Alter assessment_templates.folder_id to NOT NULL
    op.alter_column(
        "assessment_templates",
        "folder_id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )


def downgrade() -> None:
    """Revert folder_id to nullable."""
    # Revert assessments.folder_id to nullable
    op.alter_column(
        "assessments",
        "folder_id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )

    # Revert assessment_templates.folder_id to nullable
    op.alter_column(
        "assessment_templates",
        "folder_id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )
