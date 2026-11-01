from fastapi import APIRouter, Request, status

from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.core.rate_limit import login_limiter
from app.core.security import create_access_token
from app.models import Shop, User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse, ShopOut, UserOut
from app.services.auth import authenticate

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _me(db: DbSession, user: User) -> MeResponse:
    shop = db.get(Shop, user.shop_id)
    return MeResponse(user=UserOut.model_validate(user), shop=ShopOut.model_validate(shop))


@router.post("/login", response_model=LoginResponse, summary="Log in with username and password")
def login(body: LoginRequest, request: Request, db: DbSession) -> LoginResponse:
    username = body.username.strip()
    client_ip = request.client.host if request.client else "unknown"
    limit_key = f"{username.lower()}|{client_ip}"

    if login_limiter.is_blocked(limit_key):
        raise AppError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "too_many_attempts",
            "Too many wrong attempts. Try again in 15 minutes.",
        )

    user = authenticate(db, username, body.password)
    if user is None:
        login_limiter.record_failure(limit_key)
        raise AppError(
            status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "Wrong username or password"
        )

    login_limiter.reset(limit_key)
    me = _me(db, user)
    token = create_access_token(user.id, user.shop_id, user.role)
    return LoginResponse(access_token=token, user=me.user, shop=me.shop)


@router.get("/me", response_model=MeResponse, summary="Current user and their shop")
def me(user: CurrentUser, db: DbSession) -> MeResponse:
    return _me(db, user)
