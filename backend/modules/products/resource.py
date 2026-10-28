"""BACKEND: the admin-managed product catalog. Shoppers read it through backend/modules/shop."""

from backend.framework import AdminPolicy, Field, Resource
from backend.modules.products.service import before_save
from database.models.products import ProductsRecord

resource = Resource(
    key="products",
    label="Manage products",
    singular="Product",
    model=ProductsRecord,
    fields=(
        Field("name", "Name", kind="text", required=True, max_length=120, default=""),
        Field("price", "Price", kind="decimal", required=True, minimum=0, max_length=120, default="0.00"),
        Field("description", "Description", kind="textarea", required=False, max_length=10000, default=""),
    ),
    search=("name", "description"),
    columns=("name", "price"),
    policy=AdminPolicy(),
    list_template="products/index.html",
    on_save=before_save,
    description="Add and edit the products shown in the shop. Deleting a product removes it from the shop.",
)
