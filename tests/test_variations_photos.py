"""Product variations (up to 4 priced options) and extra gallery photos, from admin form to cart."""

import re
from io import BytesIO

from database import db
from database.models import CartItem, ProductImage, ProductsRecord, ProductVariation
from tests.conftest import api_request, csrf, login, post_form
from tests.test_product_images import admin_client, png_bytes

OPTIONS = {
    "variation_label_1": "Box of 5",
    "variation_price_1": "270",
    "variation_label_2": "Box of 10",
    "variation_price_2": "540.00",
    "variation_label_3": "Box of 15",
    "variation_price_3": "810",
    "variation_label_4": "Individual pieces",
    "variation_price_4": "60",
}


def save_product(admin, path="/app/products/new", photos=(), **fields):
    """Post the admin product form the way the browser does, including extra photos."""
    data = {"csrf_token": csrf(admin), "name": "Chocolate Éclair", "price": "60.00", "description": "Yum.", **fields}
    if photos:
        data["more_photos"] = [(BytesIO(raw), f"photo-{i}.png") for i, raw in enumerate(photos)]
    return admin.post(path, data=data, content_type="multipart/form-data")


def create_with_options(app, **extra):
    admin = admin_client(app)
    assert save_product(admin, **{**OPTIONS, **extra}).status_code == 303
    with app.app_context():
        product = db.session.scalar(db.select(ProductsRecord).order_by(ProductsRecord.id.desc()))
        return admin, product.id


def variation_ids(app, product_id):
    with app.app_context():
        rows = db.session.scalars(
            db.select(ProductVariation).where(ProductVariation.product_id == product_id).order_by(ProductVariation.position)
        ).all()
        return {row.label: row.id for row in rows}


def test_admin_saves_four_options_and_shop_shows_them(app, client, users):
    admin, product_id = create_with_options(app)

    page = client.get(f"/products/{product_id}").get_data(as_text=True)  # signed out: a read-only price list
    for label in ("Box of 5", "Box of 10", "Box of 15", "Individual pieces"):
        assert label in page
    assert "from ₱60.00" in page and 'name="variation_id"' not in page

    listing = client.get("/products").get_data(as_text=True)
    assert "variation-chips" in listing and "Box of 15" in listing and "from ₱60.00" in listing

    login(client)
    signed_in = client.get(f"/products/{product_id}").get_data(as_text=True)
    assert signed_in.count('name="variation_id"') == 4
    assert re.search(r'product-price" id="product-price">₱270\.00', signed_in) or "₱270.00" in signed_in

    form = admin.get(f"/app/products/{product_id}/edit").get_data(as_text=True)
    assert 'value="Box of 10"' in form and 'value="540.00"' in form  # saved rows are prefilled
    assert "Box of 15" in admin.get(f"/app/products/{product_id}").get_data(as_text=True)


def test_invalid_option_rows_are_rejected_with_a_message(app, users):
    admin = admin_client(app)
    cases = {
        "price but no label": {"variation_price_1": "10"},
        "label but no price": {"variation_label_1": "Box"},
        "negative price": {"variation_label_1": "Box", "variation_price_1": "-5"},
        "not a number": {"variation_label_1": "Box", "variation_price_1": "abc"},
        "three decimals": {"variation_label_1": "Box", "variation_price_1": "1.234"},
        "too long": {"variation_label_1": "x" * 61, "variation_price_1": "5"},
        "duplicate labels": {
            "variation_label_1": "Box",
            "variation_price_1": "5",
            "variation_label_2": "box",
            "variation_price_2": "6",
        },
    }
    for name, fields in cases.items():
        response = save_product(admin, **{"variation_label_1": "", "variation_price_1": "", **fields})
        assert response.status_code == 422, name
        assert 'class="field-error"' in response.get_data(as_text=True), name
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ProductsRecord.id))) == 0
        assert db.session.scalar(db.select(db.func.count(ProductVariation.id))) == 0


def test_editing_updates_in_place_and_blank_rows_remove_options(app, users):
    admin, product_id = create_with_options(app)
    before = variation_ids(app, product_id)
    with app.app_context():
        version = db.session.get(ProductsRecord, product_id).version

    changed = {**OPTIONS, "variation_price_2": "500", "variation_label_4": "", "variation_price_4": ""}
    response = save_product(admin, f"/app/products/{product_id}/edit", version=version, **changed)
    assert response.status_code == 303

    after = variation_ids(app, product_id)
    assert after == {k: v for k, v in before.items() if k != "Individual pieces"}  # same rows, one removed
    with app.app_context():
        price = db.session.scalar(db.select(ProductVariation.price).where(ProductVariation.label == "Box of 10"))
        assert str(price) == "500.00"
        assert db.session.get(ProductsRecord, product_id).version == version + 1  # the edit counts as a save


def test_json_api_edits_leave_options_and_photos_alone(app, users):
    admin, product_id = create_with_options(app)
    with app.app_context():
        version = db.session.get(ProductsRecord, product_id).version
    result = api_request(admin, "PATCH", f"/api/v1/products/{product_id}", {"version": version, "name": "Renamed"})
    assert result.status_code == 200, result.get_data(as_text=True)
    assert len(variation_ids(app, product_id)) == 4


def test_cart_prices_each_option_and_requires_a_choice(app, client, users):
    _, product_id = create_with_options(app)
    other_admin = admin_client(app)
    assert save_product(other_admin, name="Mug", price="120.50").status_code == 303
    with app.app_context():
        mug_id = db.session.scalar(db.select(ProductsRecord.id).where(ProductsRecord.name == "Mug"))
    ids = variation_ids(app, product_id)
    login(client)

    # A product with options cannot be added without choosing one of its own options.
    assert post_form(client, f"/cart/add/{product_id}", quantity="1").status_code == 303
    assert post_form(client, f"/cart/add/{product_id}", quantity="1", variation_id="99999").status_code == 303
    mug_option = None
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(CartItem.id))) == 0

    # Two different options are two lines; the same option twice increases one line.
    assert post_form(client, f"/cart/add/{product_id}", quantity="2", variation_id=ids["Box of 5"]).status_code == 303
    assert post_form(client, f"/cart/add/{product_id}", quantity="1", variation_id=ids["Box of 5"]).status_code == 303
    assert post_form(client, f"/cart/add/{product_id}", quantity="1", variation_id=ids["Box of 15"]).status_code == 303
    # A product without options ignores any option id that is posted.
    mug_option = ids["Box of 5"]
    assert post_form(client, f"/cart/add/{mug_id}", quantity="1", variation_id=mug_option).status_code == 303
    assert post_form(client, f"/cart/add/{mug_id}", quantity="1").status_code == 303  # same single row

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(CartItem.id))) == 3
        plain = db.session.scalar(db.select(CartItem).where(CartItem.product_id == mug_id))
        assert plain.variation_id is None and plain.quantity == 2

    cart = client.get("/cart").get_data(as_text=True)
    assert "Box of 5" in cart and "Box of 15" in cart
    assert "₱270.00 each" in cart and "₱810.00 each" in cart
    # 3 x 270 + 1 x 810 + 2 x 120.50
    assert "1861.00" in cart
    checkout = client.get("/checkout").get_data(as_text=True)
    assert "(Box of 5)" in checkout and "1861.00" in checkout


def test_removing_an_option_removes_it_from_carts(app, client, users):
    admin, product_id = create_with_options(app)
    ids = variation_ids(app, product_id)
    login(client)
    post_form(client, f"/cart/add/{product_id}", quantity="1", variation_id=ids["Individual pieces"])
    post_form(client, f"/cart/add/{product_id}", quantity="1", variation_id=ids["Box of 5"])
    with app.app_context():
        version = db.session.get(ProductsRecord, product_id).version

    blank = {**OPTIONS, "variation_label_4": "", "variation_price_4": ""}
    assert save_product(admin, f"/app/products/{product_id}/edit", version=version, **blank).status_code == 303
    cart = client.get("/cart").get_data(as_text=True)
    assert 'cart-variation">Individual pieces' not in cart and 'cart-variation">Box of 5' in cart


def test_deleting_a_product_removes_its_options_and_photos(app, users):
    admin, product_id = create_with_options(app)
    with app.app_context():
        version = db.session.get(ProductsRecord, product_id).version
    assert save_product(admin, f"/app/products/{product_id}/edit", version=version, photos=[png_bytes()], **OPTIONS)
    with app.app_context():
        version = db.session.get(ProductsRecord, product_id).version
    assert api_request(admin, "DELETE", f"/api/v1/products/{product_id}", {"version": version}).status_code == 204
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ProductVariation.id))) == 0
        assert db.session.scalar(db.select(db.func.count(ProductImage.id))) == 0


def test_extra_photos_upload_show_in_gallery_and_remove(app, client, users):
    admin = admin_client(app)
    cover = png_bytes(color="#ff0000")
    extras = [png_bytes(size=(10, 10), color="#00ff00"), png_bytes(size=(12, 12), color="#0000ff")]
    data = {"csrf_token": csrf(admin), "name": "Cake", "price": "10", "description": "", "image": (BytesIO(cover), "c.png")}
    data["more_photos"] = [(BytesIO(raw), f"x{i}.png") for i, raw in enumerate(extras)]
    assert admin.post("/app/products/new", data=data, content_type="multipart/form-data").status_code == 303
    with app.app_context():
        product = db.session.scalar(db.select(ProductsRecord))
        product_id = product.id
        photo_ids = [image.id for image in product.images]
        assert len(photo_ids) == 2 and product.has_image

    served = client.get(f"/products/{product_id}/photos/{photo_ids[0]}")  # public, like the cover
    assert served.status_code == 200 and served.mimetype == "image/png"
    assert client.get(f"/products/{product_id + 1}/photos/{photo_ids[0]}").status_code == 404  # wrong product

    page = client.get(f"/products/{product_id}").get_data(as_text=True)
    assert page.count("data-gallery-thumb") == 3  # cover + 2 extras
    assert f"/products/{product_id}/photos/{photo_ids[1]}" in page
    listing = client.get("/products").get_data(as_text=True)
    assert f"/photos/{photo_ids[0]}" not in listing  # cards only use the cover

    with app.app_context():
        version = db.session.get(ProductsRecord, product_id).version
    edit = f"/app/products/{product_id}/edit"
    assert f"/products/{product_id}/photos/{photo_ids[0]}" in admin.get(edit).get_data(as_text=True)
    removed = save_product(admin, edit, version=version, remove_photo=str(photo_ids[0]))
    assert removed.status_code == 303
    assert client.get(f"/products/{product_id}/photos/{photo_ids[0]}").status_code == 404
    assert client.get(f"/products/{product_id}/photos/{photo_ids[1]}").status_code == 200


def test_photo_limit_and_bad_files(app, users):
    admin = admin_client(app)
    good = png_bytes()
    assert save_product(admin, photos=[good] * 6).status_code == 422  # 5 is the limit
    for raw in (b"not an image", b"GIF89a\x01\x00\x01\x00\x00\x00\x00;"):
        assert save_product(admin, photos=[good, raw]).status_code == 422
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ProductsRecord.id))) == 0  # nothing half-saved

    assert save_product(admin, photos=[good] * 5).status_code == 303
    with app.app_context():
        product = db.session.scalar(db.select(ProductsRecord))
        product_id, version = product.id, product.version
    over = save_product(admin, f"/app/products/{product_id}/edit", version=version, photos=[good])
    assert over.status_code == 422 and "5 extra photos" in over.get_data(as_text=True)
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ProductImage.id))) == 5
