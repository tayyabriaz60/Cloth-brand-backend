import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import bcrypt
import jwt

from app.core.config import get_settings

JWT_ALGORITHM = "HS256"
BCRYPT_MAX_BYTES = 72
DEFAULT_BCRYPT_ROUNDS = 12
TEST_BCRYPT_ROUNDS = 4


def _bcrypt_rounds() -> int:
    # Pytest sets this while a test is running. Production never has it.
    if "PYTEST_CURRENT_TEST" in os.environ:
        return TEST_BCRYPT_ROUNDS
    return DEFAULT_BCRYPT_ROUNDS


@dataclass(frozen=True)
class TokenData:
    user_id: uuid.UUID
    shop_id: uuid.UUID
    role: str


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        raise ValueError("Password is too long")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=_bcrypt_rounds())).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("ascii"))
    except ValueError:
        return False


@lru_cache
def dummy_password_hash() -> str:
    """Checked when the username does not exist, so a failed login takes the same time.

    Computed lazily so bcrypt does not slow down serverless cold starts.
    """
    return hash_password("timing-equaliser-not-a-real-password")


def create_access_token(user_id: uuid.UUID, shop_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "shop_id": str(shop_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenData | None:
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "shop_id", "role", "exp"]},
        )
        return TokenData(
            user_id=uuid.UUID(payload["sub"]),
            shop_id=uuid.UUID(payload["shop_id"]),
            role=str(payload["role"]),
        )
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
