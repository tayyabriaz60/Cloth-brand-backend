from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel


class ShopPublic(ORMModel):
    id: UUID
    name_ur: str
    name_en: str | None
    address: str | None
    phone: str | None
    footer_text: str | None
    paper_width: int
    auto_print: bool


class ShopPatch(ORMModel):
    name_ur: str | None = Field(default=None, min_length=1, max_length=120)
    name_en: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=30)
    footer_text: str | None = Field(default=None, max_length=300)
    paper_width: int | None = Field(default=None)
    auto_print: bool | None = None
