"""Add product variations and extra product images

Revision ID: d41f7a09b3c2
Revises: c8e2f41a6d05
Create Date: 2026-11-02 17:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd41f7a09b3c2'
down_revision = 'c8e2f41a6d05'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('product_images',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('image_data', sa.LargeBinary(), nullable=False),
    sa.Column('image_type', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_images_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_images'))
    )
    with op.batch_alter_table('product_images', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_product_images_product_id'), ['product_id'], unique=False)

    op.create_table('product_variations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('label', sa.String(length=60), nullable=False),
    sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.CheckConstraint('position >= 1 AND position <= 4', name=op.f('ck_product_variations_valid_position')),
    sa.CheckConstraint('price >= 0', name=op.f('ck_product_variations_valid_price')),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_variations_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_variations')),
    sa.UniqueConstraint('product_id', 'position', name='one_variation_per_slot')
    )
    with op.batch_alter_table('product_variations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_product_variations_product_id'), ['product_id'], unique=False)


def downgrade():
    with op.batch_alter_table('product_variations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_product_variations_product_id'))

    op.drop_table('product_variations')
    with op.batch_alter_table('product_images', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_product_images_product_id'))

    op.drop_table('product_images')
