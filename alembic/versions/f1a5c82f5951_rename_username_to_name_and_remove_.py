"""rename username to name and remove unique

Revision ID: f1a5c82f5951
Revises: 5877e14505f2
Create Date: 2026-02-07 17:59:53.048232

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a5c82f5951"
down_revision: str | Sequence[str] | None = "5877e14505f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the unique index/constraint on username
    op.drop_index(op.f("ix_users_username"), table_name="users")

    # Rename username column to name
    op.alter_column("users", "username", new_column_name="name")


def downgrade() -> None:
    """Downgrade schema."""
    # Rename name column back to username
    op.alter_column("users", "name", new_column_name="username")

    # Recreate the unique index/constraint on username
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
