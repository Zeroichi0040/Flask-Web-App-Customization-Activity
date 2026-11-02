"""Add product subheading

Revision ID: c8e2f41a6d05
Revises: b3c1a7d92e40
Create Date: 2026-11-02 16:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8e2f41a6d05'
down_revision = 'b3c1a7d92e40'
branch_labels = None
depends_on = None


def upgrade():
    # server_default fills the column for products that already exist (it is NOT NULL).
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subheading', sa.String(length=160), server_default='', nullable=False))


def downgrade():
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('subheading')
