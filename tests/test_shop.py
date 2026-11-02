import re

import pytest

from database import db
from database.models import CartItem, Order, ProductsRecord
from tests.conftest import api_request, login, post_form


def links(html: bytes) -> set[str]:
    return set(re.findall(r'href="([^"#]+)"', html.decode().replace("&amp;", "&")))


@pytest.fixture
def product_ids(app, users):
    admin = app.test_client()
    login(admin, "owner@example.com")
    ids = []
    for name, price in (("Tote bag", "250.00"), ("Mug", "120.50")):
        result = api_request(admin, "POST", "/api/v1/products", {"name": name, "price": price, "description": "Nice."})
        assert result.status_code == 201, result.get_data(as_text=True)
        ids.append(result.json["data"]["id"])
    return ids


def test_products_are_public_and_come_from_the_database(client, product_ids):
    first, second = product_ids
    listing = client.get("/products")
    assert listing.status_code == 200
    assert b"Tote bag" in listing.data and b"Mug" in listing.data
    assert {f"/products/{first}", f"/products/{second}"} <= links(listing.data)
    single = client.get(f"/products/{first}")
    assert single.status_code == 200
    assert b"250.00" in single.data
    assert "/products" in links(single.data)
    assert client.get("/products/999999").status_code == 404


def test_subheading_shows_on_the_product_page_only_when_set(app, client, users, product_ids):
    admin = app.test_client()
    login(admin, "owner@example.com")
    created = api_request(admin, "POST", "/api/v1/products", {
        "name": "Eclair", "price": "60.00", "subheading": "A little chocolate magic.", "description": "Yum."
    })
    assert created.status_code == 201, created.get_data(as_text=True)
    with_sub = created.json["data"]["id"]
    page = client.get(f"/products/{with_sub}").get_data(as_text=True)
    assert "A little chocolate magic." in page and "product-subheading" in page
    assert "A little chocolate magic." not in client.get("/products").get_data(as_text=True)
    plain = client.get(f"/products/{product_ids[0]}").get_data(as_text=True)
    assert "product-subheading" not in plain
    too_long = api_request(admin, "POST", "/api/v1/products", {
        "name": "X", "price": "1", "subheading": "x" * 161
    })
    assert too_long.status_code == 422


def test_logged_out_header_basket_goes_to_sign_in(client, product_ids):
    found = links(client.get("/products").data)
    assert "/products" in found
    assert "/auth/login?next=/cart" in found
    single = client.get(f"/products/{product_ids[0]}")
    assert f"/auth/login?next=/products/{product_ids[0]}" in links(single.data)


def test_cart_and_checkout_require_an_account(client, product_ids):
    for path in ("/cart", "/checkout"):
        response = client.get(path)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]
    response = post_form(client, f"/cart/add/{product_ids[0]}", quantity="1")
    assert response.status_code == 302 and "/auth/login" in response.headers["Location"]
    assert client.post("/checkout", data={}).status_code in (302, 400)


def test_signed_in_cart_flow_and_nav_links(app, client, users, product_ids):
    login(client)
    first, second = product_ids
    assert client.get("/checkout").status_code == 303
    assert post_form(client, f"/cart/add/{first}", quantity="2").status_code == 303
    assert post_form(client, f"/cart/add/{first}", quantity="1").status_code == 303
    assert post_form(client, f"/cart/add/{second}", quantity="1").status_code == 303
    assert post_form(client, f"/cart/add/{second}", quantity="0").status_code == 303
    cart = client.get("/cart")
    assert cart.status_code == 200
    assert b"Tote bag" in cart.data and b"Mug" in cart.data
    assert b"870.50" in cart.data
    assert {"/products", "/cart", "/checkout"} <= links(cart.data)
    assert b'<span class="basket-number" aria-hidden="true">4</span>' in cart.data
    with app.app_context():
        item = db.session.scalar(db.select(CartItem).where(CartItem.product_id == second))
        item_id = item.id
    assert post_form(client, f"/cart/items/{item_id}/update", quantity="5").status_code == 303
    assert b'<span class="basket-number" aria-hidden="true">8</span>' in client.get("/cart").data
    assert post_form(client, f"/cart/items/{item_id}/remove").status_code == 303
    assert b'<span class="basket-number" aria-hidden="true">3</span>' in client.get("/cart").data
    other = app.test_client()
    login(other, "grace@example.com")
    assert post_form(other, f"/cart/items/{item_id}/remove").status_code == 404
    with app.app_context():
        mine = db.session.scalar(db.select(CartItem).where(CartItem.product_id == first))
        assert post_form(other, f"/cart/items/{mine.id}/remove").status_code == 404


def test_cart_lines_show_a_product_thumbnail(app, client, users, product_ids):
    login(client)
    with_photo, without_photo = product_ids
    with app.app_context():
        product = db.session.get(ProductsRecord, with_photo)
        product.image_data, product.image_type = b"not-a-real-image", "image/png"
        db.session.commit()
        version = product.version
    post_form(client, f"/cart/add/{with_photo}", quantity="1")
    post_form(client, f"/cart/add/{without_photo}", quantity="1")
    html = client.get("/cart").get_data(as_text=True)
    assert f"/products/{with_photo}/image?v={version}" in html
    assert html.count("cart-thumb-photo") == 1
    assert html.count("cart-thumb-icon") == 1


def test_checkout_creates_order_snapshots_and_clears_cart(app, client, users, product_ids):
    login(client)
    post_form(client, f"/cart/add/{product_ids[0]}", quantity="2")
    bad = post_form(client, "/checkout", full_name="Ada", email="not-an-email", address="", city="")
    assert bad.status_code == 422
    good = post_form(client, "/checkout", full_name="Ada Student", email="ada@example.com",
                     address="1 Main St", city="Cebu", notes="Leave at the door")
    assert good.status_code == 303
    assert good.headers["Location"].endswith("/products")
    with app.app_context():
        order = db.session.scalar(db.select(Order))
        assert order is not None
        assert order.status == "placed"
        assert order.full_name == "Ada Student"
        assert str(order.total) == "500.00"
        assert len(order.items) == 1
        assert order.items[0].product_name == "Tote bag"
        assert order.items[0].quantity == 2
        assert str(order.items[0].unit_price) == "250.00"
        assert db.session.scalar(db.select(db.func.count(CartItem.id))) == 0


def test_every_shop_link_resolves_when_signed_in(client, users, product_ids):
    login(client)
    post_form(client, f"/cart/add/{product_ids[0]}", quantity="1")
    for path in ("/products", f"/products/{product_ids[0]}", "/cart", "/checkout"):
        for link in links(client.get(path).data):
            if link.startswith("/") and not link.startswith(("/static/", "/auth/logout")):
                assert client.get(link).status_code == 200, f"{path} links to broken {link}"


def test_customer_can_list_and_view_only_their_own_orders(app, client, users, product_ids):
    login(client)
    post_form(client, f"/cart/add/{product_ids[0]}", quantity="2")
    placed = post_form(client, "/checkout", full_name="Ada Student", email="ada@example.com",
                       address="1 Main St", city="Cebu", notes="Leave at the door")
    assert placed.status_code == 303
    with app.app_context():
        order = db.session.scalar(db.select(Order))
        order_id = order.id

    listing = client.get("/my-orders")
    assert listing.status_code == 200
    assert f"/my-orders/{order_id}" in links(listing.data)
    assert b"Order #" in listing.data and b"Placed" in listing.data

    detail = client.get(f"/my-orders/{order_id}")
    assert detail.status_code == 200
    assert b"Tote bag" in detail.data
    assert b"Ada Student" in detail.data
    assert b"Leave at the door" in detail.data

    other = app.test_client()
    login(other, "grace@example.com")
    assert other.get(f"/my-orders/{order_id}").status_code == 404


def test_my_orders_requires_sign_in(client):
    for path in ("/my-orders", "/my-orders/1"):
        response = client.get(path)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]
