from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import StockMovement
from tests.conftest import CASHIER_PASSWORD, OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_product


def test_adjust_below_zero_rejected_and_rolled_back(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, opening=Decimal("10"))
    token = login(client, owner.username, OWNER_PASSWORD)
    before = db.scalar(select(func.count()).select_from(StockMovement))

    response = client.post(
        "/api/stock/adjust",
        json={
            "product_id": str(product.id),
            "qty_change": "-10.50",
            "adjust_reason": "missing",
            "note": "too much",
        },
        headers=auth_header(token),
    )
    listed = client.get("/api/stock", headers=auth_header(token))

    assert response.status_code == 422
    assert response.json()["code"] == "insufficient_stock"
    assert listed.json()["items"][0]["qty"] == "10.00"
    assert db.scalar(select(func.count()).select_from(StockMovement)) == before


def test_adjust_without_reason_or_note_rejected(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)
    headers = auth_header(token)

    no_reason = client.post(
        "/api/stock/adjust",
        json={"product_id": str(product.id), "qty_change": "-1", "note": "torn"},
        headers=headers,
    )
    no_note = client.post(
        "/api/stock/adjust",
        json={"product_id": str(product.id), "qty_change": "-1", "adjust_reason": "damaged"},
        headers=headers,
    )
    zero = client.post(
        "/api/stock/adjust",
        json={
            "product_id": str(product.id),
            "qty_change": "0",
            "adjust_reason": "damaged",
            "note": "noop",
        },
        headers=headers,
    )

    assert no_reason.status_code == 422
    assert no_note.status_code == 422
    assert zero.status_code == 422
    assert zero.json()["code"] == "qty_change_zero"
    assert db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.reason == "adjust")) == 0


def test_count_no_difference_writes_nothing(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, opening=Decimal("10"))
    token = login(client, owner.username, OWNER_PASSWORD)
    before = db.scalar(select(func.count()).select_from(StockMovement))

    response = client.post(
        "/api/stock/count",
        json={"product_id": str(product.id), "counted_qty": "10"},
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json() == {"changed": False}
    assert db.scalar(select(func.count()).select_from(StockMovement)) == before


def test_cashier_purchase_but_not_adjust_or_count(client: TestClient, db: Session) -> None:
    shop, _, cashier = make_shop(db, "Alpha")
    product = add_product(db, shop.id, cost_price=100, opening=Decimal("10"))
    token = login(client, cashier.username, CASHIER_PASSWORD)
    headers = auth_header(token)

    bought = client.post(
        "/api/stock/purchase",
        json={"product_id": str(product.id), "qty": "2", "cost_price": 999},
        headers=headers,
    )
    adjusted = client.post(
        "/api/stock/adjust",
        json={
            "product_id": str(product.id),
            "qty_change": "-1",
            "adjust_reason": "damaged",
            "note": "torn",
        },
        headers=headers,
    )
    counted = client.post(
        "/api/stock/count",
        json={"product_id": str(product.id), "counted_qty": "8"},
        headers=headers,
    )
    stock = client.get("/api/stock", headers=headers)
    movements = client.get("/api/stock/movements", headers=headers)
    summary = client.get("/api/stock/summary", headers=headers)

    assert bought.status_code == 201
    assert "cost_price" not in bought.json()
    assert adjusted.status_code == 403
    assert adjusted.json()["code"] == "owner_only"
    assert counted.status_code == 403
    assert counted.json()["code"] == "owner_only"
    assert "cost_price" not in stock.json()["items"][0]
    assert "unit_cost" not in movements.json()["items"][0]
    assert "unit_cost" not in summary.json()["recent_movements"][0]
    assert "unit_cost" not in summary.json()["recent_purchases"][0]
