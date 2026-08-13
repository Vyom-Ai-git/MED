"""phase9_integration_deliveries

Revision ID: e8d9f10a11b2
Revises: 9f82d3e14b56
Create Date: 2026-08-13 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8d9f10a11b2'
down_revision: Union[str, Sequence[str], None] = '9f82d3e14b56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add integration_deliveries table."""
    op.create_table(
        'integration_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=100), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('destination', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_deliveries_id'), 'integration_deliveries', ['id'], unique=False)
    op.create_index(op.f('ix_integration_deliveries_event_id'), 'integration_deliveries', ['event_id'], unique=True)
    op.create_index(op.f('ix_integration_deliveries_event_type'), 'integration_deliveries', ['event_type'], unique=False)
    op.create_index(op.f('ix_integration_deliveries_status'), 'integration_deliveries', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_integration_deliveries_status'), table_name='integration_deliveries')
    op.drop_index(op.f('ix_integration_deliveries_event_type'), table_name='integration_deliveries')
    op.drop_index(op.f('ix_integration_deliveries_event_id'), table_name='integration_deliveries')
    op.drop_index(op.f('ix_integration_deliveries_id'), table_name='integration_deliveries')
    op.drop_table('integration_deliveries')
