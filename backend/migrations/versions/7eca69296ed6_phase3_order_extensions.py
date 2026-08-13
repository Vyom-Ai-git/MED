"""phase3_order_extensions

Revision ID: 7eca69296ed6
Revises: ef7acd808f6c
Create Date: 2026-08-13 00:08:02.292223

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = '7eca69296ed6'
down_revision: Union[str, Sequence[str], None] = 'ef7acd808f6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — Phase 3 order extensions."""
    conn = op.get_bind()

    # 1. Add new order_items columns as nullable first to handle existing rows
    op.add_column('order_items', sa.Column('test_name_snapshot', sa.String(), nullable=True))
    op.add_column('order_items', sa.Column('test_code_snapshot', sa.String(), nullable=True))
    op.add_column('order_items', sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('order_items', sa.Column('quantity', sa.Integer(), nullable=True))
    op.add_column('order_items', sa.Column('discount', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('order_items', sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('order_items', sa.Column('created_at', sa.DateTime(), nullable=True))

    # 2. Backfill existing rows from the tests table join
    conn.execute(text("""
        UPDATE order_items oi
        SET
            test_name_snapshot = COALESCE(t.name, 'Unknown Test'),
            test_code_snapshot  = COALESCE(t.code, 'UNKNOWN'),
            unit_price          = COALESCE(oi.price, 0.00),
            quantity            = 1,
            discount            = 0.00,
            total               = COALESCE(oi.price, 0.00),
            created_at          = NOW()
        FROM tests t
        WHERE oi.test_id = t.id
    """))
    # Handle any orphaned items without a test
    conn.execute(text("""
        UPDATE order_items
        SET
            test_name_snapshot = COALESCE(test_name_snapshot, 'Unknown Test'),
            test_code_snapshot  = COALESCE(test_code_snapshot, 'UNKNOWN'),
            unit_price          = COALESCE(unit_price, 0.00),
            quantity            = COALESCE(quantity, 1),
            discount            = COALESCE(discount, 0.00),
            total               = COALESCE(total, 0.00),
            created_at          = COALESCE(created_at, NOW())
        WHERE test_name_snapshot IS NULL
    """))

    # 3. Now set NOT NULL constraints
    op.alter_column('order_items', 'test_name_snapshot', nullable=False)
    op.alter_column('order_items', 'test_code_snapshot', nullable=False)
    op.alter_column('order_items', 'unit_price', nullable=False)
    op.alter_column('order_items', 'quantity', nullable=False)
    op.alter_column('order_items', 'discount', nullable=False)
    op.alter_column('order_items', 'total', nullable=False)
    op.alter_column('order_items', 'created_at', nullable=False)

    # 4. Update FK to SET NULL (preserve history if test is later deleted)
    op.alter_column('order_items', 'test_id', existing_type=sa.INTEGER(), nullable=True)
    op.drop_constraint('order_items_test_id_fkey', 'order_items', type_='foreignkey')
    op.create_foreign_key(None, 'order_items', 'tests', ['test_id'], ['id'], ondelete='SET NULL')

    # 5. Drop old 'price' column
    op.drop_column('order_items', 'price')

    # 6. Add orders columns — subtotal nullable first for backfill
    op.add_column('orders', sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('orders', sa.Column('notes', sa.Text(), nullable=True))

    # 7. Backfill subtotal = total_amount for existing orders
    conn.execute(text("UPDATE orders SET subtotal = total_amount WHERE subtotal IS NULL"))
    op.alter_column('orders', 'subtotal', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('orders', 'notes')
    op.drop_column('orders', 'subtotal')

    op.add_column('order_items', sa.Column('price', sa.NUMERIC(precision=10, scale=2),
                                            server_default='0.00', nullable=False))
    # Copy unit_price back into price
    conn = op.get_bind()
    conn.execute(text("UPDATE order_items SET price = unit_price"))

    op.drop_constraint(None, 'order_items', type_='foreignkey')
    op.create_foreign_key('order_items_test_id_fkey', 'order_items', 'tests',
                          ['test_id'], ['id'], ondelete='CASCADE')
    op.alter_column('order_items', 'test_id', existing_type=sa.INTEGER(), nullable=False)
    op.drop_column('order_items', 'created_at')
    op.drop_column('order_items', 'total')
    op.drop_column('order_items', 'discount')
    op.drop_column('order_items', 'quantity')
    op.drop_column('order_items', 'unit_price')
    op.drop_column('order_items', 'test_code_snapshot')
    op.drop_column('order_items', 'test_name_snapshot')
