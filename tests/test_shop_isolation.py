from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import ShopScope
from app.core.security import create_access_token, hash_password
from app.models import Customer
from tests.conftest import CASHIER_PASSWORD, OWNER_PASSWORD, login, make_shop


def test_same_username_and_password_in_two_shops_is_refused(
    client: TestClient, db: Session
) -> None:
    make_shop(db, "Alpha")
    make_shop(db, "Beta")

    response = client.post(
        "/api/auth/login", json={"username": "owner", "password": OWNER_PASSWORD}
    )

    assert response.status_code == 401


def test_same_username_logs_into_the_shop_whose_password_matches(
    client: TestClient, db: Session
) -> None:
    make_shop(db, "Alpha")
    shop_b, owner_b, _ = make_shop(db, "Beta")
    owner_b.password_hash = hash_password("beta-only-pass")
    db.commit()

    token = login(client, "owner", "beta-only-pass")
    body = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    assert body["shop"]["id"] == str(shop_b.id)
    assert body["user"]["id"] == str(owner_b.id)


def test_token_with_other_shop_id_is_rejected(client: TestClient, db: Session) -> None:
    _, owner_a, _ = make_shop(db, "Alpha")
    shop_b, _, _ = make_shop(db, "Beta")
    forged = create_access_token(owner_a.id, shop_b.id, owner_a.role)

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


def test_me_only_shows_own_shop(client: TestClient, db: Session) -> None:
    shop_a, _, cashier_a = make_shop(db, "Alpha")
    make_shop(db, "Beta")
    token = login(client, cashier_a.username, CASHIER_PASSWORD)

    body = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    assert body["shop"]["id"] == str(shop_a.id)


def test_shop_scope_never_returns_other_shop_rows(db: Session) -> None:
    shop_a, owner_a, _ = make_shop(db, "Alpha")
    shop_b, owner_b, _ = make_shop(db, "Beta")
    customer_a = Customer(shop_id=shop_a.id, name="A customer")
    customer_b = Customer(shop_id=shop_b.id, name="B customer")
    db.add_all([customer_a, customer_b])
    db.commit()

    scope_a = ShopScope(db=db, user=owner_a)

    visible = list(db.scalars(scope_a.select(Customer)))
    assert [c.id for c in visible] == [customer_a.id]
    assert scope_a.get(Customer, customer_b.id) is None
    assert scope_a.get(Customer, customer_a.id) is not None
    assert ShopScope(db=db, user=owner_b).get(Customer, customer_a.id) is None
