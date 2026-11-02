from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from decimal import Decimal

from tests.conftest import OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_customer, add_product, make_bill_body, post_bill


def test_payment_cannot_exceed_balance(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    customer = add_customer(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)
    post_bill(
        client,
        token,
        make_bill_body(product.id, payment_type="udhaar", paid_amount=0, customer_id=customer.id),
    )

    too_much = client.post(
        "/api/ledger/payment",
        json={"customer_id": str(customer.id), "amount": 701},
        headers=auth_header(token),
    )
    ok = client.post(
        "/api/ledger/payment",
        json={"customer_id": str(customer.id), "amount": 200},
        headers=auth_header(token),
    )

    assert too_much.status_code == 422
    assert too_much.json()["code"] == "payment_exceeds_balance"
    assert ok.status_code == 201
    customers = client.get("/api/customers", headers=auth_header(token)).json()["items"]
    assert customers[0]["balance"] == 500


def test_change_password_rules(client: TestClient, db: Session) -> None:
    _, owner, _ = make_shop(db, "Alpha")
    token = login(client, owner.username, OWNER_PASSWORD)
    headers = auth_header(token)

    wrong = client.post(
        "/api/auth/change-password",
        json={"current_password": "nope", "new_password": "new-password-1"},
        headers=headers,
    )
    same = client.post(
        "/api/auth/change-password",
        json={"current_password": OWNER_PASSWORD, "new_password": OWNER_PASSWORD},
        headers=headers,
    )
    short = client.post(
        "/api/auth/change-password",
        json={"current_password": OWNER_PASSWORD, "new_password": "short"},
        headers=headers,
    )
    ok = client.post(
        "/api/auth/change-password",
        json={"current_password": OWNER_PASSWORD, "new_password": "new-password-1"},
        headers=headers,
    )

    assert wrong.status_code == 422
    assert wrong.json()["code"] == "wrong_password"
    assert same.status_code == 422
    assert same.json()["code"] == "same_password"
    assert short.status_code == 422
    assert ok.status_code == 204
    assert client.post(
        "/api/auth/login", json={"username": owner.username, "password": "new-password-1"}
    ).status_code == 200


def test_dashboard_known_dataset(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, min_stock=Decimal("20"), opening=Decimal("10"))
    customer = add_customer(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)
    post_bill(
        client,
        token,
        make_bill_body(product.id, payment_type="udhaar", paid_amount=200, customer_id=customer.id),
    )

    dash = client.get("/api/dashboard", headers=auth_header(token)).json()

    assert dash["today_sales"] == 700
    assert dash["today_received"] == 200
    assert dash["total_udhaar"] == 500
    assert dash["low_stock_count"] == 1
    assert dash["top_udhaar"][0]["balance"] == 500
    assert len(dash["week_sales"]) == 7
    assert dash["week_sales"][-1]["total"] == 700
    assert dash["last_bills"][0]["total"] == 700
