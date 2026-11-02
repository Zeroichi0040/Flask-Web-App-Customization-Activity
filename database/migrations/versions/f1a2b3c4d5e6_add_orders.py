"""Add persisted orders and order item snapshots.

Revision ID: f1a2b3c4d5e6
Revises: e5a90c3d7b18
Create Date: 2026-11-02
"""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "e5a90c3d7b18"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="placed"),
        sa.Column("full_name", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("address", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('placed', 'preparing', 'out_for_delivery', 'completed', 'cancelled')",
            name="valid_order_status",
        ),
        sa.CheckConstraint("total >= 0", name="valid_order_total"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("variation_id", sa.Integer(), sa.ForeignKey("product_variations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_name", sa.String(length=120), nullable=False),
        sa.Column("variation_label", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity >= 1", name="valid_order_item_quantity"),
        sa.CheckConstraint("unit_price >= 0 AND subtotal >= 0", name="valid_order_item_amounts"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade():
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
