from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import CASHIER_PASSWORD, OWNER_PASSWORD, auth_header, login, make_shop

NEW_CASHIER_PASSWORD = "new-cashier-1"


def test_owner_creates_cashier_and_duplicate_username_is_rejected(client: TestClient, db: Session) -> None:
    _shop, owner, _ = make_shop(db, "Alpha")
    token = login(client, owner.username, OWNER_PASSWORD)
    body = {"name": "Ali", "username": "ali", "password": NEW_CASHIER_PASSWORD}

    created = client.post("/api/users", json=body, headers=auth_header(token))
    duplicate = client.post("/api/users", json=body, headers=auth_header(token))

    assert created.status_code == 201
    assert created.json()["username"] == "ali"
    assert created.json()["role"] == "cashier"
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "conflict"


def test_cashier_cannot_create_users(client: TestClient, db: Session) -> None:
    _shop, _, cashier = make_shop(db, "Alpha")
    token = login(client, cashier.username, CASHIER_PASSWORD)

    response = client.post(
        "/api/users",
        json={"name": "Ali", "username": "ali", "password": NEW_CASHIER_PASSWORD},
        headers=auth_header(token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "owner_only"


def test_deactivated_user_cannot_log_in(client: TestClient, db: Session) -> None:
    _shop, owner, cashier = make_shop(db, "Alpha")
    token = login(client, owner.username, OWNER_PASSWORD)

    patched = client.patch(
        f"/api/users/{cashier.id}",
        json={"is_active": False},
        headers=auth_header(token),
    )
    login_attempt = client.post(
        "/api/auth/login",
        json={"username": cashier.username, "password": CASHIER_PASSWORD},
    )

    assert patched.status_code == 200
    assert patched.json()["is_active"] is False
    assert login_attempt.status_code == 401
    assert login_attempt.json()["code"] == "invalid_credentials"
