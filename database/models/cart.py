"""DATABASE: one row per product in a signed-in user's cart."""

from database import db


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    # Which option of the product was chosen; NULL for products without options.
    variation_id = db.Column(
        db.Integer, db.ForeignKey("product_variations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    product = db.relationship("ProductsRecord")
    variation = db.relationship("ProductVariation")
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", "variation_id", name="one_row_per_product_variation_in_cart"),
        # NULLs never collide in a unique constraint, so plain (no option) rows get their own index.
        db.Index(
            "one_plain_row_per_product_in_cart",
            "user_id",
            "product_id",
            unique=True,
            sqlite_where=db.text("variation_id IS NULL"),
            postgresql_where=db.text("variation_id IS NULL"),
        ),
        db.CheckConstraint("quantity >= 1 AND quantity <= 99", name="valid_quantity"),
    )
