from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import StockMovement
from tests.conftest import OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_product, make_bill_body, post_bill


def test_done_test_balances_300_290_285_280(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, name_ur="Cotton", cost_price=100, opening=Decimal("0"))
    token = login(client, owner.username, OWNER_PASSWORD)
    headers = auth_header(token)

    bought = client.post(
        "/api/stock/purchase",
        json={
            "product_id": str(product.id),
            "qty": "300",
            "cost_price": 400,
            "supplier_name": "Ali Mills",
            "note": "bale",
        },
        headers=headers,
    )
    sold = post_bill(client, token, make_bill_body(product.id, qty="10", rate=200))
    damaged = client.post(
        "/api/stock/adjust",
        json={
            "product_id": str(product.id),
            "qty_change": "-5",
            "adjust_reason": "damaged",
            "note": "torn",
        },
        headers=headers,
    )
    counted = client.post(
        "/api/stock/count",
        json={"product_id": str(product.id), "counted_qty": "280", "note": "month end"},
        headers=headers,
    )
    stock = client.get("/api/stock", headers=headers)
    history = client.get(f"/api/stock/movements?product_id={product.id}", headers=headers)

    assert bought.status_code == 201
    assert bought.json()["qty"] == "300.00"
    assert bought.json()["cost_price"] == 400
    assert sold.status_code == 201
    assert damaged.status_code == 201
    assert damaged.json()["qty"] == "285.00"
    assert counted.status_code == 200
    assert counted.json()["changed"] is True
    assert counted.json()["movement"]["balance_after"] == "280.00"
    assert counted.json()["movement"]["adjust_reason"] == "count_correction"
    assert stock.json()["items"][0]["qty"] == "280.00"
    balances = [row["balance_after"] for row in reversed(history.json()["items"])]
    assert balances == ["300.00", "290.00", "285.00", "280.00"]
    reasons = [row["reason"] for row in reversed(history.json()["items"])]
    assert reasons == ["purchase", "sale", "adjust", "adjust"]


def test_decimals_and_rounding(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, opening=Decimal("0"))
    token = login(client, owner.username, OWNER_PASSWORD)
    headers = auth_header(token)

    bought = client.post(
        "/api/stock/purchase",
        json={"product_id": str(product.id), "qty": "3.5", "note": "cut"},
        headers=headers,
    )
    adjusted = client.post(
        "/api/stock/adjust",
        json={
            "product_id": str(product.id),
            "qty_change": "0.25",
            "adjust_reason": "measurement",
            "note": "remeasure",
        },
        headers=headers,
    )

    assert bought.json()["qty"] == "3.50"
    assert adjusted.json()["qty"] == "3.75"
    history = client.get(f"/api/stock/movements?product_id={product.id}", headers=headers)
    changes = [row["qty_change"] for row in reversed(history.json()["items"])]
    assert changes == ["3.50", "0.25"]


def test_purchase_stores_supplier_name_and_note(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, opening=Decimal("0"))
    token = login(client, owner.username, OWNER_PASSWORD)

    client.post(
        "/api/stock/purchase",
        json={
            "product_id": str(product.id),
            "qty": "2",
            "supplier_name": "Ali Mills",
            "note": "bale",
        },
        headers=auth_header(token),
    )

    movement = db.scalar(select(StockMovement).where(StockMovement.reason == "purchase"))
    assert movement is not None
    assert movement.supplier_name == "Ali Mills"
    assert movement.note == "bale"
    assert db.scalar(select(func.count()).select_from(StockMovement)) == 1
