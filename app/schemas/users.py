from uuid import UUID

from pydantic import Field

from app.core.constants import MIN_PASSWORD_LENGTH
from app.schemas.common import ORMModel


class ChangePasswordIn(ORMModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class UserCreateIn(ORMModel):
    name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class UserStaffOut(ORMModel):
    id: UUID
    name: str
    username: str
    role: str
    is_active: bool


class UserStaffList(ORMModel):
    items: list[UserStaffOut]


class UserPatch(ORMModel):
    is_active: bool
