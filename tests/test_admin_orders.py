from database import db
from database.models import Order
from tests.conftest import login, post_form


def make_order(app, user_id):
    with app.app_context():
        order = Order(
            user_id=user_id, full_name="Ada Student", email="ada@example.com",
            phone="", address="1 Main St", city="Cebu", notes="",
            total="250.00",
        )
        db.session.add(order)
        db.session.commit()
        return order.id


def test_admin_can_view_and_update_order_status(app, users):
    client = app.test_client()
    login(client, "owner@example.com")
    order_id = make_order(app, users["ada"])
    page = client.get("/admin/orders")
    assert page.status_code == 200
    assert f"Order #{order_id}".encode() in page.data
    response = post_form(client, f"/admin/orders/{order_id}/status", status="preparing")
    assert response.status_code == 303
    with app.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == "preparing"


def test_non_admin_cannot_manage_orders(app, users):
    client = app.test_client()
    login(client)
    order_id = make_order(app, users["ada"])
    assert client.get("/admin/orders").status_code == 403
    assert post_form(client, f"/admin/orders/{order_id}/status", status="completed").status_code == 403


def test_invalid_order_status_is_rejected(app, users):
    client = app.test_client()
    login(client, "owner@example.com")
    order_id = make_order(app, users["ada"])
    response = post_form(client, f"/admin/orders/{order_id}/status", status="not-a-status")
    assert response.status_code == 400
    with app.app_context():
        assert db.session.get(Order, order_id).status == "placed"


def test_missing_csrf_is_rejected(app, users):
    client = app.test_client()
    login(client, "owner@example.com")
    order_id = make_order(app, users["ada"])
    assert client.post(f"/admin/orders/{order_id}/status", data={"status": "completed"}).status_code == 400
