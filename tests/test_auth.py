import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.rate_limit import MAX_LOGIN_FAILURES
from app.core.security import DEFAULT_BCRYPT_ROUNDS, TEST_BCRYPT_ROUNDS, _bcrypt_rounds
from tests.conftest import CASHIER_PASSWORD, login, make_shop


def test_login_success_returns_token_user_and_shop(client: TestClient, db: Session) -> None:
    shop, _, cashier = make_shop(db, "Alpha")

    response = client.post(
        "/api/auth/login", json={"username": cashier.username, "password": CASHIER_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"] == {"id": str(cashier.id), "name": cashier.name, "role": "cashier"}
    assert body["shop"]["id"] == str(shop.id)
    assert body["shop"]["name_ur"] == shop.name_ur
    assert "password_hash" not in body["user"]


def test_login_wrong_password_fails(client: TestClient, db: Session) -> None:
    _, _, cashier = make_shop(db, "Alpha")

    response = client.post(
        "/api/auth/login", json={"username": cashier.username, "password": "wrong"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_login_unknown_user_fails(client: TestClient, db: Session) -> None:
    make_shop(db, "Alpha")

    response = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})

    assert response.status_code == 401


def test_login_inactive_user_fails(client: TestClient, db: Session) -> None:
    _, _, cashier = make_shop(db, "Alpha")
    cashier.is_active = False
    db.commit()

    response = client.post(
        "/api/auth/login", json={"username": cashier.username, "password": CASHIER_PASSWORD}
    )

    assert response.status_code == 401


def test_login_is_blocked_after_too_many_failures(client: TestClient, db: Session) -> None:
    _, _, cashier = make_shop(db, "Alpha")
    payload = {"username": cashier.username, "password": "wrong"}
    for _ in range(MAX_LOGIN_FAILURES):
        assert client.post("/api/auth/login", json=payload).status_code == 401

    blocked = client.post(
        "/api/auth/login", json={"username": cashier.username, "password": CASHIER_PASSWORD}
    )

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "too_many_attempts"


def test_me_returns_current_user(client: TestClient, db: Session) -> None:
    shop, _, cashier = make_shop(db, "Alpha")
    token = login(client, cashier.username, CASHIER_PASSWORD)

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(cashier.id)
    assert response.json()["shop"]["id"] == str(shop.id)


def test_me_without_token_is_401(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == {"code": "not_authenticated", "message": "Please log in again"}


def test_me_with_bad_token_is_401(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401


def test_validation_error_has_stable_shape(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": ""})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_root_redirects_to_docs(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_health_runs_select_1(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_bcrypt_is_cheap_only_under_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _bcrypt_rounds() == TEST_BCRYPT_ROUNDS
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert _bcrypt_rounds() == DEFAULT_BCRYPT_ROUNDS
