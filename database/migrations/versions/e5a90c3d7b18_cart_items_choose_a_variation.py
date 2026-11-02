"""Let a cart item point at a product variation

Existing rows keep working: their variation_id stays NULL, which means "the product itself".
SQLite cannot change constraints in place, so batch mode rebuilds cart_items (keeping its data).

Revision ID: e5a90c3d7b18
Revises: d41f7a09b3c2
Create Date: 2026-11-02 17:21:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5a90c3d7b18'
down_revision = 'd41f7a09b3c2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('cart_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('variation_id', sa.Integer(), nullable=True))
        batch_op.drop_constraint(batch_op.f('one_row_per_product_in_cart'), type_='unique')
        batch_op.create_index(batch_op.f('ix_cart_items_variation_id'), ['variation_id'], unique=False)
        batch_op.create_index('one_plain_row_per_product_in_cart', ['user_id', 'product_id'], unique=True, sqlite_where=sa.text('variation_id IS NULL'), postgresql_where=sa.text('variation_id IS NULL'))
        batch_op.create_unique_constraint('one_row_per_product_variation_in_cart', ['user_id', 'product_id', 'variation_id'])
        batch_op.create_foreign_key(batch_op.f('fk_cart_items_variation_id_product_variations'), 'product_variations', ['variation_id'], ['id'], ondelete='CASCADE')


def downgrade():
    # Rows that chose an option would collide with the old one-row-per-product rule, so drop them first.
    op.execute('DELETE FROM cart_items WHERE variation_id IS NOT NULL')
    with op.batch_alter_table('cart_items', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cart_items_variation_id_product_variations'), type_='foreignkey')
        batch_op.drop_constraint('one_row_per_product_variation_in_cart', type_='unique')
        batch_op.drop_index('one_plain_row_per_product_in_cart', sqlite_where=sa.text('variation_id IS NULL'), postgresql_where=sa.text('variation_id IS NULL'))
        batch_op.drop_index(batch_op.f('ix_cart_items_variation_id'))
        batch_op.create_unique_constraint(batch_op.f('one_row_per_product_in_cart'), ['user_id', 'product_id'])
        batch_op.drop_column('variation_id')
