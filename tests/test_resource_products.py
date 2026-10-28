"""Product catalog integration test. Only administrators manage products."""

from tests.conftest import api_request, login


def test_products_resource_is_admin_only(app, client, users):
    login(client)
    payload = {"name": "Example record", "price": "12.50", "description": "Saved through the generated API."}
    assert api_request(client, "POST", "/api/v1/products", payload).status_code == 403
    assert client.get("/app/products").status_code == 403

    admin = app.test_client()
    login(admin, "owner@example.com")
    result = api_request(admin, "POST", "/api/v1/products", payload)
    assert result.status_code == 201, result.get_data(as_text=True)
    identifier = result.json["data"]["id"]
    assert admin.get(f"/api/v1/products/{identifier}").status_code == 200
    assert admin.get("/app/products").status_code == 200
    assert api_request(admin, "DELETE", f"/api/v1/products/{identifier}", {"version": 1}).status_code == 204
