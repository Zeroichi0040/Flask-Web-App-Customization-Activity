"""DATABASE: Products. Change fields here and create a reviewed migration."""

from database import db
from database.models.base import OwnedRecord


class ProductsRecord(OwnedRecord, db.Model):
    __tablename__ = "products"
    name = db.Column(db.String(120), nullable=False, default="")
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
