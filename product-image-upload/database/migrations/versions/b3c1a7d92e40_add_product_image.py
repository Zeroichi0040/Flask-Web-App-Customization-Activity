"""Add product image

Revision ID: b3c1a7d92e40
Revises: 79bafd60a46b
Create Date: 2026-10-29 14:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c1a7d92e40'
down_revision = '79bafd60a46b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_data', sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column('image_type', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('image_type')
        batch_op.drop_column('image_data')
