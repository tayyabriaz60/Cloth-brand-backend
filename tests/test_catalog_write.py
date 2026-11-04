from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import CASHIER_PASSWORD, OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_product


def test_owner_creates_product_with_opening_stock(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    token = login(client, owner.username, OWNER_PASSWORD)

    response = client.post(
        "/api/products",
        json={
            "name_ur": "ململ",
            "unit": "gaz",
            "cost_price": 380,
            "sale_price": 480,
            "opening_stock": "12.50",
        },
        headers=auth_header(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name_ur"] == "ململ"
    assert body["cost_price"] == 380
    assert body["stock"] == "12.50"


def test_product_create_and_edit_are_owner_only(client: TestClient, db: Session) -> None:
    shop, owner, cashier = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    owner_token = login(client, owner.username, OWNER_PASSWORD)
    cashier_token = login(client, cashier.username, CASHIER_PASSWORD)
    write = {"name_ur": "ململ", "unit": "gaz", "cost_price": 100, "sale_price": 200}

    create = client.post("/api/products", json=write, headers=auth_header(cashier_token))
    edit_cashier = client.patch(
        f"/api/products/{product.id}",
        json={"sale_price": 250},
        headers=auth_header(cashier_token),
    )
    edit_owner = client.patch(
        f"/api/products/{product.id}",
        json={"sale_price": 250},
        headers=auth_header(owner_token),
    )

    assert create.status_code == 403
    assert create.json()["code"] == "owner_only"
    assert edit_cashier.status_code == 403
    assert edit_cashier.json()["code"] == "owner_only"
    assert edit_owner.status_code == 200
    assert edit_owner.json()["sale_price"] == 250
    assert edit_owner.json()["cost_price"] == product.cost_price
