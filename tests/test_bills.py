from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Bill, StockMovement
from tests.conftest import OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_customer, add_product, make_bill_body, post_bill


def test_bill_updates_stock_and_ledger_for_gaz(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, opening=Decimal("10"), sale_price=200)
    customer = add_customer(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)
    body = make_bill_body(
        product.id,
        qty="3.5",
        rate=200,
        payment_type="udhaar",
        paid_amount=100,
        customer_id=customer.id,
    )

    response = post_bill(client, token, body)

    assert response.status_code == 201
    data = response.json()
    assert data["subtotal"] == 700
    assert data["total"] == 700
    assert data["paid_amount"] == 100
    assert data["items"][0]["qty"] == "3.50"
    assert data["items"][0]["line_total"] == 700
    assert data["bill_no"] == 1
    stock = db.scalar(
        select(func.coalesce(func.sum(StockMovement.qty_change), 0)).where(
            StockMovement.product_id == product.id
        )
    )
    assert Decimal(str(stock)) == Decimal("6.50")
    ledger = client.get(f"/api/customers/{customer.id}/ledger", headers=auth_header(token)).json()
    assert ledger["items"][0]["entry_type"] == "udhaar"
    assert ledger["items"][0]["amount"] == 600
    assert ledger["items"][0]["bill_no"] == 1


def test_same_bill_uuid_is_idempotent(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)
    bill_id = uuid4()
    body = make_bill_body(product.id, bill_id=bill_id)

    first = post_bill(client, token, body)
    second = post_bill(client, token, body)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["bill_no"] == second.json()["bill_no"]
    assert db.scalar(select(func.count()).select_from(Bill)) == 1
    movements = db.scalars(select(StockMovement).where(StockMovement.reason == "sale")).all()
    assert len(movements) == 1


def test_udhaar_without_customer_rejected(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)
    body = make_bill_body(product.id, payment_type="udhaar", paid_amount=0)

    response = post_bill(client, token, body)

    assert response.status_code == 422
    assert response.json()["code"] == "udhaar_needs_customer"
    assert db.scalar(select(func.count()).select_from(Bill)) == 0


def test_cash_with_wrong_paid_amount_rejected(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)
    body = make_bill_body(product.id, payment_type="cash", paid_amount=1)

    response = post_bill(client, token, body)

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_paid_amount"


def test_percent_and_amount_discount(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)

    amount = post_bill(client, token, make_bill_body(product.id, discount=50, discount_type="amount"))
    percent = post_bill(
        client, token, make_bill_body(product.id, bill_id=uuid4(), discount=10, discount_type="percent")
    )

    assert amount.status_code == 201
    assert amount.json()["subtotal"] == 700
    assert amount.json()["discount"] == 50
    assert amount.json()["total"] == 650
    assert percent.status_code == 201
    assert percent.json()["discount"] == 70
    assert percent.json()["total"] == 630


def test_discount_above_subtotal_rejected(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)

    response = post_bill(
        client, token, make_bill_body(product.id, discount=9999, discount_type="amount", paid_amount=0)
    )

    assert response.status_code == 422
    assert response.json()["code"] == "discount_too_high"


def test_bill_numbers_sequential_per_shop(client: TestClient, db: Session) -> None:
    shop_a, owner_a, _ = make_shop(db, "Alpha")
    shop_b, owner_b, _ = make_shop(db, "Beta")
    pa = add_product(db, shop_a.id)
    pb = add_product(db, shop_b.id)
    ta = login(client, owner_a.username, OWNER_PASSWORD)
    tb = login(client, owner_b.username, OWNER_PASSWORD)

    a1 = post_bill(client, ta, make_bill_body(pa.id))
    a2 = post_bill(client, ta, make_bill_body(pa.id, bill_id=uuid4()))
    b1 = post_bill(client, tb, make_bill_body(pb.id))

    assert a1.json()["bill_no"] == 1
    assert a2.json()["bill_no"] == 2
    assert b1.json()["bill_no"] == 1
