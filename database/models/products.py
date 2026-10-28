"""DATABASE: Products. Change fields here and create a reviewed migration."""

from database import db
from database.models.base import OwnedRecord


class ProductsRecord(OwnedRecord, db.Model):
    __tablename__ = "products"
    name = db.Column(db.String(120), nullable=False, default="")
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    description = db.Column(db.Text, nullable=False, default="")
