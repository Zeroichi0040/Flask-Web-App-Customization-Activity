"""DATABASE: persisted customer orders and immutable line-item snapshots."""

from database import db
from database.models.user import utcnow


ORDER_STATUSES = (
    ("placed", "Placed"),
    ("preparing", "Preparing"),
    ("out_for_delivery", "Out for delivery"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
)


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = db.Column(db.String(24), nullable=False, default="placed", index=True)
    full_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    phone = db.Column(db.String(30), nullable=False, default="")
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    notes = db.Column(db.Text, nullable=False, default="")
    total = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan",
                            order_by="OrderItem.id")
    customer = db.relationship("User")
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('placed', 'preparing', 'out_for_delivery', 'completed', 'cancelled')",
            name="valid_order_status",
        ),
        db.CheckConstraint("total >= 0", name="valid_order_total"),
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    variation_id = db.Column(db.Integer, db.ForeignKey("product_variations.id", ondelete="SET NULL"), nullable=True)
    product_name = db.Column(db.String(120), nullable=False)
    variation_label = db.Column(db.String(60), nullable=False, default="")
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    order = db.relationship("Order", back_populates="items")
    __table_args__ = (
        db.CheckConstraint("quantity >= 1", name="valid_order_item_quantity"),
        db.CheckConstraint("unit_price >= 0 AND subtotal >= 0", name="valid_order_item_amounts"),
    )
