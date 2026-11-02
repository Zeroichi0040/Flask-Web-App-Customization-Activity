"""DATABASE: Products. Change fields here and create a reviewed migration."""

from database import db
from database.models.base import OwnedRecord


class ProductsRecord(OwnedRecord, db.Model):
    __tablename__ = "products"
    name = db.Column(db.String(120), nullable=False, default="")
    subheading = db.Column(db.String(160), nullable=False, default="", server_default="")
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    description = db.Column(db.Text, nullable=False, default="")
    # The product photo is stored in the database (like the file library) so it survives
    # hosts with an ephemeral filesystem. The bytes are deferred: listing products never loads them.
    image_data = db.deferred(db.Column(db.LargeBinary, nullable=True))
    image_type = db.Column(db.String(20), nullable=True)  # "image/png", "image/jpeg" or "image/webp"

    @property
    def has_image(self):
        return self.image_type is not None

    @property
    def image(self):
        """Public image path for the JSON API and CSV export; empty when there is no image."""
        return f"/products/{self.id}/image?v={self.version}" if self.has_image else ""

    # Up to 4 priced options (e.g. "Box of 5") and a few extra photos besides the cover image above.
    variations = db.relationship(
        "ProductVariation",
        order_by="ProductVariation.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    images = db.relationship(
        "ProductImage",
        order_by="ProductImage.position, ProductImage.id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def from_price(self):
        """The lowest price shoppers can pay: the cheapest option, or the product price without options."""
        return min((v.price for v in self.variations), default=self.price)


class ProductVariation(db.Model):
    """One priced option of a product, such as "Box of 5". Slots 1-4; edited in place so carts keep working."""

    __tablename__ = "product_variations"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(60), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    __table_args__ = (
        db.UniqueConstraint("product_id", "position", name="one_variation_per_slot"),
        db.CheckConstraint("position >= 1 AND position <= 4", name="valid_position"),
        db.CheckConstraint("price >= 0", name="valid_price"),
    )


class ProductImage(db.Model):
    """An extra photo for a product's gallery. The cover photo stays on the product itself."""

    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False, default=1)
    image_data = db.deferred(db.Column(db.LargeBinary, nullable=False))
    image_type = db.Column(db.String(20), nullable=False)
