from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import OwnerUser, Scope
from app.schemas.users import UserCreateIn, UserPatch, UserStaffList, UserStaffOut
from app.services import users as users_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserStaffList, summary="Staff of this shop (owner)")
def list_users(_owner: OwnerUser, scope: Scope) -> UserStaffList:
    return UserStaffList(items=users_service.list_users(scope))


@router.post(
    "",
    response_model=UserStaffOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a cashier (owner)",
)
def create_user(_owner: OwnerUser, scope: Scope, body: UserCreateIn) -> UserStaffOut:
    return users_service.create_cashier(scope, body)


@router.patch("/{user_id}", response_model=UserStaffOut, summary="Activate or deactivate (owner)")
def patch_user(_owner: OwnerUser, scope: Scope, user_id: UUID, body: UserPatch) -> UserStaffOut:
    return users_service.patch_user(scope, user_id, body)
