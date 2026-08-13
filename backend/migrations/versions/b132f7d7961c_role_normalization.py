"""role_normalization

Revision ID: b132f7d7961c
Revises: 255d1b36ec8c
Create Date: 2026-08-12 23:08:11.433604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b132f7d7961c'
down_revision: Union[str, Sequence[str], None] = '255d1b36ec8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Normalize existing pathologist role to reviewer role
    op.execute("UPDATE users SET role = 'reviewer' WHERE role = 'pathologist'")


def downgrade() -> None:
    """Downgrade schema."""
    # Revert reviewer role back to pathologist
    op.execute("UPDATE users SET role = 'pathologist' WHERE role = 'reviewer'")
