import re

import pytest

from database import db
from database.models import CartItem
from tests.conftest import api_request, login, post_form


def links(html: bytes) -> set[str]:
    return set(re.findall(r'href="([^"#]+)"', html.decode().replace("&amp;", "&")))


@pytest.fixture
def product_ids(app, users):
    """Two products created the way an administrator would, through the admin-only API."""
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

    assert client.get("/checkout").status_code == 303  # empty cart is sent back to the shop

    assert post_form(client, f"/cart/add/{first}", quantity="2").status_code == 303
    assert post_form(client, f"/cart/add/{first}", quantity="1").status_code == 303  # adds to the same row
    assert post_form(client, f"/cart/add/{second}", quantity="1").status_code == 303
    assert post_form(client, f"/cart/add/{second}", quantity="0").status_code == 303  # rejected, not added

    cart = client.get("/cart")
    assert cart.status_code == 200
    assert b"Tote bag" in cart.data and b"Mug" in cart.data
    assert b"870.50" in cart.data  # 3 x 250.00 + 1 x 120.50
    assert {"/products", "/cart", "/checkout"} <= links(cart.data)
    assert b"Cart (4)" in cart.data  # left-hand navigation shows the item count

    with app.app_context():
        item = db.session.scalar(db.select(CartItem).where(CartItem.product_id == second))
        item_id = item.id
    assert post_form(client, f"/cart/items/{item_id}/update", quantity="5").status_code == 303
    assert b"Cart (8)" in client.get("/cart").data
    assert post_form(client, f"/cart/items/{item_id}/remove").status_code == 303
    assert b"Cart (3)" in client.get("/cart").data

    # Someone else's cart row cannot be changed.
    other = app.test_client()
    login(other, "grace@example.com")
    assert post_form(other, f"/cart/items/{item_id}/remove").status_code == 404
    with app.app_context():
        mine = db.session.scalar(db.select(CartItem).where(CartItem.product_id == first))
        assert post_form(other, f"/cart/items/{mine.id}/remove").status_code == 404


def test_checkout_validates_and_confirms(client, users, product_ids):
    login(client)
    post_form(client, f"/cart/add/{product_ids[0]}", quantity="1")
    page = client.get("/checkout")
    assert page.status_code == 200
    assert b"Tote bag" in page.data and b"ada@example.com" in page.data

    bad = post_form(client, "/checkout", full_name="Ada", email="not-an-email", address="", city="")
    assert bad.status_code == 422

    good = post_form(
        client, "/checkout", full_name="Ada Student", email="ada@example.com", address="1 Main St", city="Cebu"
    )
    assert good.status_code == 303
    assert good.headers["Location"].endswith("/checkout")
    assert b"Orders are not saved yet" in client.get("/checkout").data


def test_every_shop_link_resolves_when_signed_in(client, users, product_ids):
    login(client)
    post_form(client, f"/cart/add/{product_ids[0]}", quantity="1")
    for path in ("/products", f"/products/{product_ids[0]}", "/cart", "/checkout"):
        for link in links(client.get(path).data):
            if link.startswith("/") and not link.startswith(("/static/", "/auth/logout")):
                assert client.get(link).status_code == 200, f"{path} links to broken {link}"
