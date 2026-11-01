from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import dummy_password_hash, verify_password
from app.models import User


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Return the active user whose username and password match, else None.

    Usernames are unique per shop, not globally. If the same username exists in
    several shops, only a password that matches exactly one of them logs in.
    """
    candidates = list(
        db.scalars(select(User).where(User.username == username, User.is_active.is_(True)))
    )
    if not candidates:
        verify_password(password, dummy_password_hash())
        return None
    matches = [user for user in candidates if verify_password(password, user.password_hash)]
    return matches[0] if len(matches) == 1 else None
