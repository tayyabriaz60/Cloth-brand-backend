from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import CASHIER_PASSWORD, OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_product, make_bill_body, post_bill


def test_cashier_product_and_dashboard_hide_money_totals(client: TestClient, db: Session) -> None:
    shop, owner, cashier = make_shop(db, "Alpha")
    product = add_product(db, shop.id, cost_price=80, sale_price=200, opening=Decimal("10"))
    owner_token = login(client, owner.username, OWNER_PASSWORD)
    cashier_token = login(client, cashier.username, CASHIER_PASSWORD)
    post_bill(client, owner_token, make_bill_body(product.id, qty="1", rate=200))

    owner_products = client.get("/api/products", headers=auth_header(owner_token)).json()["items"][0]
    cashier_products = client.get("/api/products", headers=auth_header(cashier_token)).json()["items"][0]
    owner_dash = client.get("/api/dashboard", headers=auth_header(owner_token)).json()
    cashier_dash = client.get("/api/dashboard", headers=auth_header(cashier_token)).json()

    assert "cost_price" in owner_products
    assert owner_products["cost_price"] == 80
    assert "cost_price" not in cashier_products
    assert "today_sales" in owner_dash
    assert "week_sales" in owner_dash
    assert "today_sales" not in cashier_dash
    assert "week_sales" not in cashier_dash
    assert "today_received" not in cashier_dash
    assert "total" not in cashier_dash["last_bills"][0]
    assert "paid_amount" not in cashier_dash["last_bills"][0]
