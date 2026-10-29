"""Admins can attach an image when they add or edit a product; shoppers see it on the shop pages."""

from io import BytesIO

from PIL import Image

from database import db
from database.models import ProductsRecord
from tests.conftest import api_request, csrf, login


def png_bytes(size=(8, 6), color="#173d35"):
    stream = BytesIO()
    Image.new("RGB", size, color).save(stream, format="PNG")
    return stream.getvalue()


def submit_product(client, path="/app/products/new", image=None, filename="photo.png", **extra):
    data = {"csrf_token": csrf(client), "name": "Tote bag", "price": "250.00", "description": "Canvas.", **extra}
    if image is not None:
        data["image"] = (BytesIO(image), filename)
    return client.post(path, data=data, content_type="multipart/form-data")


def admin_client(app):
    admin = app.test_client()
    login(admin, "owner@example.com")
    return admin


def test_admin_form_accepts_an_image_and_shop_shows_it(app, client, users):
    admin = admin_client(app)
    assert b'enctype="multipart/form-data"' in admin.get("/app/products/new").data
    raw = png_bytes()
    assert submit_product(admin, image=raw).status_code == 303
    with app.app_context():
        product = db.session.scalar(db.select(ProductsRecord))
        identifier, version = product.id, product.version
        assert product.image_type == "image/png" and product.has_image

    served = client.get(f"/products/{identifier}/image")  # shoppers need no account
    assert served.status_code == 200 and served.mimetype == "image/png"
    assert Image.open(BytesIO(served.data)).size == (8, 6)
    assert f"/products/{identifier}/image?v={version}" in client.get("/products").get_data(as_text=True)
    assert f"/products/{identifier}/image?v={version}" in client.get(f"/products/{identifier}").get_data(as_text=True)
    assert admin.get(f"/app/products/{identifier}").status_code == 200
    assert admin.get(f"/app/products/{identifier}/edit").status_code == 200


def test_product_without_an_image_keeps_the_placeholder(app, client, users):
    admin = admin_client(app)
    assert submit_product(admin).status_code == 303
    with app.app_context():
        identifier = db.session.scalar(db.select(ProductsRecord.id))
    assert client.get(f"/products/{identifier}/image").status_code == 404
    page = client.get(f"/products/{identifier}").get_data(as_text=True)
    assert "basket.svg" in page and "product-photo" not in page


def test_replace_and_remove_image_on_edit(app, client, users):
    admin = admin_client(app)
    submit_product(admin, image=png_bytes(color="#ff0000"))
    with app.app_context():
        product = db.session.scalar(db.select(ProductsRecord))
        identifier, version = product.id, product.version
    edit = f"/app/products/{identifier}/edit"

    # Saving without choosing a file keeps the current image.
    assert submit_product(admin, edit, version=version, name="Tote bag 2").status_code == 303
    assert client.get(f"/products/{identifier}/image").status_code == 200
    version += 1

    # Choosing a new file replaces it.
    assert submit_product(admin, edit, image=png_bytes(size=(20, 10)), version=version).status_code == 303
    assert Image.open(BytesIO(client.get(f"/products/{identifier}/image").data)).size == (20, 10)
    version += 1

    # The remove checkbox clears it.
    assert submit_product(admin, edit, version=version, remove_image="1").status_code == 303
    assert client.get(f"/products/{identifier}/image").status_code == 404


def test_invalid_uploads_are_rejected(app, users):
    admin = admin_client(app)
    for raw, name in (
        (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "evil.svg"),
        (b"not really a png", "fake.png"),
        (b"GIF89a\x01\x00\x01\x00\x00\x00\x00;", "photo.gif"),
    ):
        response = submit_product(admin, image=raw, filename=name)
        assert response.status_code == 422, name
    too_big = BytesIO()
    Image.effect_noise((1500, 1500), 90).save(too_big, format="PNG")  # incompressible, well over 2 MiB
    assert len(too_big.getvalue()) > 2 * 1024 * 1024
    assert submit_product(admin, image=too_big.getvalue()).status_code == 422
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ProductsRecord.id))) == 0


def test_uploaded_photo_metadata_is_stripped(app, client, users):
    admin = admin_client(app)
    stream = BytesIO()
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"  # EXIF "Make"; phones also store GPS the same way
    Image.new("RGB", (8, 8), "#336699").save(stream, format="JPEG", exif=exif)
    assert b"SecretCameraMaker" in stream.getvalue()
    assert submit_product(admin, image=stream.getvalue(), filename="phone.jpg").status_code == 303
    with app.app_context():
        identifier = db.session.scalar(db.select(ProductsRecord.id))
    served = client.get(f"/products/{identifier}/image")
    assert served.mimetype == "image/jpeg" and b"SecretCameraMaker" not in served.data


def test_only_admins_upload_and_the_api_stays_json_only(app, client, users):
    login(client)  # an ordinary account
    assert client.get("/app/products/new").status_code == 403
    assert submit_product(client, image=png_bytes()).status_code == 403

    admin = admin_client(app)
    submit_product(admin, image=png_bytes())
    with app.app_context():
        identifier = db.session.scalar(db.select(ProductsRecord.id))
    data = admin.get(f"/api/v1/products/{identifier}").json["data"]
    assert data["image"].startswith(f"/products/{identifier}/image")  # read-only URL, never the bytes
    assert admin.get("/api/v1/products?sort=image").status_code == 422  # not sortable
    rejected = api_request(admin, "POST", "/api/v1/products", {"name": "X", "price": "1.00", "image": "x.png"})
    assert rejected.status_code == 422
    created = api_request(admin, "POST", "/api/v1/products", {"name": "No photo", "price": "1.00"})
    assert created.status_code == 201 and created.json["data"]["image"] == ""
