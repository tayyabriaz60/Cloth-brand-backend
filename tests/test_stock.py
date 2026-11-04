from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import StockMovement
from tests.conftest import CASHIER_PASSWORD, OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_product


def test_owner_purchase_adds_movement_and_updates_cost(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, cost_price=100, opening=Decimal("10"))
    token = login(client, owner.username, OWNER_PASSWORD)

    response = client.post(
        "/api/stock/purchase",
        json={"product_id": str(product.id), "qty": "5.00", "cost_price": 250, "note": "bale"},
        headers=auth_header(token),
    )

    db.refresh(product)
    assert response.status_code == 201
    assert response.json()["qty"] == "15.00"
    assert response.json()["cost_price"] == 250
    assert product.cost_price == 250
    assert db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.reason == "purchase")) == 1


def test_cashier_purchase_ignores_cost_price(client: TestClient, db: Session) -> None:
    shop, _, cashier = make_shop(db, "Alpha")
    product = add_product(db, shop.id, cost_price=100, opening=Decimal("10"))
    token = login(client, cashier.username, CASHIER_PASSWORD)

    response = client.post(
        "/api/stock/purchase",
        json={"product_id": str(product.id), "qty": "2.00", "cost_price": 999},
        headers=auth_header(token),
    )

    db.refresh(product)
    assert response.status_code == 201
    assert response.json()["qty"] == "12.00"
    assert "cost_price" not in response.json()
    assert product.cost_price == 100
    assert db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.reason == "purchase")) == 1


def test_owner_adjust_success(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, opening=Decimal("10"))
    token = login(client, owner.username, OWNER_PASSWORD)

    response = client.post(
        "/api/stock/adjust",
        json={"product_id": str(product.id), "qty_change": "-0.50", "note": "torn end"},
        headers=auth_header(token),
    )

    assert response.status_code == 201
    assert response.json()["qty"] == "9.50"
    assert response.json()["cost_price"] == product.cost_price
    assert db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.reason == "adjust")) == 1


def test_cashier_cannot_adjust(client: TestClient, db: Session) -> None:
    shop, _, cashier = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, cashier.username, CASHIER_PASSWORD)

    response = client.post(
        "/api/stock/adjust",
        json={"product_id": str(product.id), "qty_change": "-0.50", "note": "torn end"},
        headers=auth_header(token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "owner_only"
    assert db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.reason == "adjust")) == 0


def test_adjust_without_note_rejected(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)
    headers = auth_header(token)

    missing = client.post(
        "/api/stock/adjust",
        json={"product_id": str(product.id), "qty_change": "-0.50"},
        headers=headers,
    )
    empty = client.post(
        "/api/stock/adjust",
        json={"product_id": str(product.id), "qty_change": "-0.50", "note": ""},
        headers=headers,
    )

    assert missing.status_code == 422
    assert empty.status_code == 422
    assert db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.reason == "adjust")) == 0
