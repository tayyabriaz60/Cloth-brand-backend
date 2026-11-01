import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    role: str


class ShopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name_ur: str
    name_en: str | None
    address: str | None
    phone: str | None
    footer_text: str | None
    paper_width: int
    auto_print: bool
    settings: dict[str, Any]


class MeResponse(BaseModel):
    user: UserOut
    shop: ShopOut


class LoginResponse(MeResponse):
    access_token: str
    token_type: str = "bearer"
