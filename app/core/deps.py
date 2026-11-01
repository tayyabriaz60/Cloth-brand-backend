import uuid
from dataclasses import dataclass
from typing import Annotated, Any, TypeVar

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models import User
from app.models.base import ShopOwnedMixin
from app.models.shop import ROLE_OWNER

ModelT = TypeVar("ModelT", bound=ShopOwnedMixin)

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized() -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "not_authenticated", "Please log in again")


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise _unauthorized()
    token = decode_access_token(credentials.credentials)
    if token is None:
        raise _unauthorized()
    user = db.get(User, token.user_id)
    if user is None or not user.is_active or user.shop_id != token.shop_id:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_owner(user: CurrentUser) -> User:
    # Role is read from the database, not the token, so a demoted user loses access at once.
    if user.role != ROLE_OWNER:
        raise AppError(status.HTTP_403_FORBIDDEN, "owner_only", "Only the owner can do this")
    return user


OwnerUser = Annotated[User, Depends(require_owner)]


@dataclass(frozen=True)
class ShopScope:
    """The only way routes and services should query shop-owned tables."""

    db: Session
    user: User

    @property
    def shop_id(self) -> uuid.UUID:
        return self.user.shop_id

    def select(self, model: type[ModelT]) -> Select[Any]:
        return select(model).where(model.shop_id == self.shop_id)

    def get(self, model: type[ModelT], obj_id: uuid.UUID) -> ModelT | None:
        return self.db.scalar(self.select(model).where(model.id == obj_id))


def get_shop_scope(db: DbSession, user: CurrentUser) -> ShopScope:
    return ShopScope(db=db, user=user)


Scope = Annotated[ShopScope, Depends(get_shop_scope)]
