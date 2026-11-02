import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import ShopScope
from app.core.security import create_access_token, hash_password
from app.models import Customer, Shop, User
from tests.conftest import CASHIER_PASSWORD, OWNER_PASSWORD, login, make_shop


def test_username_cannot_be_reused_in_another_shop(db: Session) -> None:
    _, owner_a, _ = make_shop(db, "Alpha")
    shop_b = Shop(name_ur="بیٹا", name_en="Beta")
    db.add(shop_b)
    db.flush()
    db.add(
        User(
            shop_id=shop_b.id,
            name="Copycat",
            username=owner_a.username,
            password_hash=hash_password(OWNER_PASSWORD),
            role="owner",
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_uppercase_username_is_rejected_by_the_database(db: Session) -> None:
    shop, _, _ = make_shop(db, "Alpha")
    db.add(
        User(
            shop_id=shop.id,
            name="Shouty",
            username="SHOUTY",
            password_hash=hash_password(OWNER_PASSWORD),
            role="cashier",
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_login_username_is_case_insensitive(client: TestClient, db: Session) -> None:
    shop_a, owner_a, _ = make_shop(db, "Alpha")
    make_shop(db, "Beta")

    token = login(client, f"  {owner_a.username.upper()} ", OWNER_PASSWORD)
    body = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    assert body["user"]["id"] == str(owner_a.id)
    assert body["shop"]["id"] == str(shop_a.id)


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
