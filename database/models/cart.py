"""DATABASE: one row per product in a signed-in user's cart."""

from database import db


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    product = db.relationship("ProductsRecord")
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="one_row_per_product_in_cart"),
        db.CheckConstraint("quantity >= 1 AND quantity <= 99", name="valid_quantity"),
    )
