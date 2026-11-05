from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.constants import COLOR_MAX, FABRIC_TYPE_MAX, UNITS
from app.schemas.common import ORMModel, QtyOut


class CategoryOut(ORMModel):
    id: UUID
    name_ur: str
    name_en: str | None
    sort_order: int


class CategoryList(ORMModel):
    items: list[CategoryOut]


class ImageOut(ORMModel):
    id: UUID
    public_url: str | None
    sort_order: int


class CategoryRef(ORMModel):
    id: UUID
    name_ur: str
    name_en: str | None


class ProductOut(ORMModel):
    id: UUID
    name_ur: str
    name_en: str | None
    design_no: str | None
    unit: str
    sale_price: int
    min_stock: QtyOut
    category: CategoryRef | None
    images: list[ImageOut]
    stock: QtyOut
    is_low_stock: bool
    is_active: bool
    fabric_type: str | None = None
    color: str | None = None


class OwnerProductOut(ProductOut):
    cost_price: int


class ProductList(ORMModel):
    items: list[ProductOut]


class OwnerProductList(ORMModel):
    items: list[OwnerProductOut]


class ProductWrite(ORMModel):
    name_ur: str = Field(min_length=1, max_length=150)
    name_en: str | None = Field(default=None, max_length=150)
    design_no: str | None = Field(default=None, max_length=50)
    unit: str = Field(examples=list(UNITS))
    cost_price: int = Field(ge=0)
    sale_price: int = Field(ge=0)
    min_stock: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    category_id: UUID | None = None
    is_active: bool = True
    opening_stock: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    fabric_type: str | None = Field(default=None, max_length=FABRIC_TYPE_MAX)
    color: str | None = Field(default=None, max_length=COLOR_MAX)


class ProductPatch(ORMModel):
    name_ur: str | None = Field(default=None, min_length=1, max_length=150)
    name_en: str | None = Field(default=None, max_length=150)
    design_no: str | None = Field(default=None, max_length=50)
    unit: str | None = None
    cost_price: int | None = Field(default=None, ge=0)
    sale_price: int | None = Field(default=None, ge=0)
    min_stock: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    category_id: UUID | None = None
    is_active: bool | None = None
    fabric_type: str | None = Field(default=None, max_length=FABRIC_TYPE_MAX)
    color: str | None = Field(default=None, max_length=COLOR_MAX)


class AttachImageIn(ORMModel):
    key: str = Field(min_length=1, max_length=300)
