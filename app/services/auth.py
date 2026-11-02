from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import dummy_password_hash, verify_password
from app.models import User
from app.models.shop import normalize_username


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Return the active user whose username and password match, else None."""
    user = db.scalar(
        select(User).where(User.username == normalize_username(username), User.is_active.is_(True))
    )
    if user is None:
        verify_password(password, dummy_password_hash())
        return None
    return user if verify_password(password, user.password_hash) else None
