from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import MIN_PASSWORD_LENGTH
from app.core.deps import ShopScope
from app.core.errors import conflict, unprocessable
from app.core.security import hash_password, verify_password
from app.models import User
from app.models.shop import ROLE_CASHIER, normalize_username
from app.schemas.users import UserCreateIn, UserPatch, UserStaffOut
from app.services.tx import commit


def change_password(user: User, current_password: str, new_password: str, db: Session) -> None:
    if not verify_password(current_password, user.password_hash):
        raise unprocessable("wrong_password", "Current password is wrong")
    if new_password == current_password:
        raise unprocessable("same_password", "New password must be different")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise unprocessable("weak_password", f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    user.password_hash = hash_password(new_password)
    db.commit()


def set_password_for_username(db: Session, username: str, new_password: str) -> str:
    """Used by the CLI script. Returns the username that was updated."""
    uname = normalize_username(username)
    user = db.scalar(select(User).where(User.username == uname))
    if user is None:
        raise LookupError("user not found")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if verify_password(new_password, user.password_hash):
        raise ValueError("New password must be different")
    user.password_hash = hash_password(new_password)
    db.commit()
    return uname


def list_users(scope: ShopScope) -> list[UserStaffOut]:
    rows = scope.db.scalars(scope.select(User).order_by(User.name)).all()
    return [UserStaffOut.model_validate(row) for row in rows]


def create_cashier(scope: ShopScope, body: UserCreateIn) -> UserStaffOut:
    username = normalize_username(body.username)
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise unprocessable("weak_password", f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    taken = scope.db.scalar(select(User).where(User.username == username))
    if taken is not None:
        raise conflict("That username is already taken")
    user = User(
        shop_id=scope.shop_id,
        name=body.name.strip(),
        username=username,
        password_hash=hash_password(body.password),
        role=ROLE_CASHIER,
    )
    scope.db.add(user)
    commit(scope)
    return UserStaffOut.model_validate(user)


def patch_user(scope: ShopScope, user_id: UUID, body: UserPatch) -> UserStaffOut:
    user = scope.require(User, user_id)
    if user.id == scope.user.id and body.is_active is False:
        raise unprocessable("cannot_modify_self", "You cannot deactivate yourself")
    user.is_active = body.is_active
    commit(scope)
    return UserStaffOut.model_validate(user)
