"""Tests run on an in-memory SQLite database and NEVER touch Neon.

Env vars are set before the app is imported. Real env vars win over .env in
pydantic-settings, so the real DATABASE_URL is never used. The Postgres URL
below points at a closed port; nothing ever connects to it.
"""

import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@127.0.0.1:1/never_used"
os.environ["DATABASE_URL_DIRECT"] = ""
os.environ["JWT_SECRET"] = "test-only-secret-at-least-32-characters-long"
os.environ["FRONTEND_URL"] = "http://localhost:5173"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.db import get_db, get_health_db  # noqa: E402
from app.core.rate_limit import login_limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Shop, User  # noqa: E402
from app.models.shop import ROLE_CASHIER, ROLE_OWNER  # noqa: E402

OWNER_PASSWORD = "owner-pass-1"
CASHIER_PASSWORD = "cashier-pass-1"


@pytest.fixture
def engine() -> Iterator[Engine]:
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(test_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def _get_test_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_health_db] = _get_test_db
    login_limiter.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    login_limiter.clear()


def make_shop(db: Session, name_en: str) -> tuple[Shop, User, User]:
    shop = Shop(name_ur=f"{name_en} اردو", name_en=name_en)
    db.add(shop)
    db.flush()
    owner = User(
        shop_id=shop.id,
        name=f"{name_en} Owner",
        username=f"owner-{name_en.lower()}",
        password_hash=hash_password(OWNER_PASSWORD),
        role=ROLE_OWNER,
    )
    cashier = User(
        shop_id=shop.id,
        name=f"{name_en} Cashier",
        username=f"cashier-{name_en.lower()}",
        password_hash=hash_password(CASHIER_PASSWORD),
        role=ROLE_CASHIER,
    )
    db.add_all([owner, cashier])
    db.commit()
    return shop, owner, cashier


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])
