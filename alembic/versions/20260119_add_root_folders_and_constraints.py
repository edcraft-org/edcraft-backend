"""add root folders and constraints

Revision ID: 20260119_add_root_folders
Revises: 7d4be8c360e2
Create Date: 2026-01-19

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260119_add_root_folders"
down_revision: str | Sequence[str] | None = "7d4be8c360e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create root folders for existing users with unique constraint and migrate data."""
    conn = op.get_bind()

    # Get all non-deleted users
    users = conn.execute(
        sa.text("SELECT id FROM users WHERE deleted_at IS NULL")
    ).fetchall()

    for (user_id,) in users:
        folder_id = str(uuid.uuid4())

        # Create root folder for user with name "My Projects"
        conn.execute(
            sa.text("""
                INSERT INTO folders (id, owner_id, parent_id, name, created_at, updated_at)
                VALUES (:id, :owner_id, NULL, 'My Projects', NOW(), NOW())
            """),
            {"id": folder_id, "owner_id": str(user_id)},
        )

        # Move existing root folders into new root folder
        conn.execute(
            sa.text("""
                UPDATE folders SET parent_id = :root_id
                WHERE owner_id = :owner_id AND parent_id IS NULL AND id != :root_id
            """),
            {"root_id": folder_id, "owner_id": str(user_id)},
        )

        # Move existing root assessments into new root folder
        conn.execute(
            sa.text("""
                UPDATE assessments SET folder_id = :root_id
                WHERE owner_id = :owner_id AND folder_id IS NULL
            """),
            {"root_id": folder_id, "owner_id": str(user_id)},
        )

        # Move existing root assessment templates into new root folder
        conn.execute(
            sa.text("""
                UPDATE assessment_templates SET folder_id = :root_id
                WHERE owner_id = :owner_id AND folder_id IS NULL
            """),
            {"root_id": folder_id, "owner_id": str(user_id)},
        )

    # Add partial unique index to enforce one root per user
    op.execute(
        sa.text("""
            CREATE UNIQUE INDEX uq_one_root_per_user
            ON folders (owner_id)
            WHERE parent_id IS NULL AND deleted_at IS NULL
        """)
    )


def downgrade() -> None:
    """Remove root folders and restore root-level items to null folder_id/parent_id."""
    conn = op.get_bind()

    # Drop the unique index first
    op.execute(sa.text("DROP INDEX IF EXISTS uq_one_root_per_user"))

    # Get all root folders
    root_folders = conn.execute(
        sa.text("""
            SELECT id, owner_id FROM folders
            WHERE parent_id IS NULL AND name = 'My Projects' AND deleted_at IS NULL
        """)
    ).fetchall()

    for folder_id, _ in root_folders:
        # Move items back to NULL
        conn.execute(
            sa.text("""
                UPDATE folders SET parent_id = NULL
                WHERE parent_id = :root_id
            """),
            {"root_id": folder_id},
        )

        conn.execute(
            sa.text("""
                UPDATE assessments SET folder_id = NULL
                WHERE folder_id = :root_id
            """),
            {"root_id": folder_id},
        )

        conn.execute(
            sa.text("""
                UPDATE assessment_templates SET folder_id = NULL
                WHERE folder_id = :root_id
            """),
            {"root_id": folder_id},
        )

        # Delete the root folder
        conn.execute(
            sa.text("DELETE FROM folders WHERE id = :root_id"),
            {"root_id": folder_id},
        )
