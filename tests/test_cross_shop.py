from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Bill, LedgerEntry, StockMovement
from tests.conftest import OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_customer, add_product, make_bill_body, post_bill


def test_shop_a_cannot_use_shop_b_ids(client: TestClient, db: Session) -> None:
    shop_a, owner_a, _ = make_shop(db, "Alpha")
    shop_b, _, _ = make_shop(db, "Beta")
    product_a = add_product(db, shop_a.id)
    product_b = add_product(db, shop_b.id)
    customer_b = add_customer(db, shop_b.id)
    token = login(client, owner_a.username, OWNER_PASSWORD)

    bill = post_bill(client, token, make_bill_body(product_b.id))
    purchase = client.post(
        "/api/stock/purchase",
        json={"product_id": str(product_b.id), "qty": "2", "note": "x"},
        headers=auth_header(token),
    )
    payment = client.post(
        "/api/ledger/payment",
        json={"customer_id": str(customer_b.id), "amount": 10},
        headers=auth_header(token),
    )
    # valid local product so we know writes would work
    ok = post_bill(client, token, make_bill_body(product_a.id))

    assert bill.status_code == 404
    assert bill.json()["code"] == "not_found"
    assert purchase.status_code == 404
    assert payment.status_code == 404
    assert ok.status_code == 201
    assert db.scalar(select(func.count()).select_from(Bill)) == 1
    assert db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.reason == "purchase")) == 0
    assert db.scalar(select(func.count()).select_from(LedgerEntry)) == 0
