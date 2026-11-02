from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.constants import CUSTOMER_LANGS, DISCOUNT_TYPES, PAYMENT_TYPES
from app.schemas.common import ORMModel, QtyOut


class BillItemIn(ORMModel):
    product_id: UUID
    qty: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    rate: int = Field(ge=0)


class BillCreateIn(ORMModel):
    id: UUID
    customer_id: UUID | None = None
    items: list[BillItemIn]
    discount: int = Field(ge=0)
    discount_type: str = Field(examples=list(DISCOUNT_TYPES))
    payment_type: str = Field(examples=list(PAYMENT_TYPES))
    paid_amount: int = Field(ge=0)
    customer_lang: str = Field(default="ur", examples=list(CUSTOMER_LANGS))
    note: str | None = Field(default=None, max_length=300)


class BillItemOut(ORMModel):
    id: UUID
    product_id: UUID
    name_snapshot: str
    qty: QtyOut
    unit: str
    rate: int
    line_total: int


class BillOut(ORMModel):
    id: UUID
    bill_no: int
    customer_id: UUID | None
    subtotal: int
    discount: int
    total: int
    paid_amount: int
    payment_type: str
    customer_lang: str
    note: str | None
    items: list[BillItemOut]
    warnings: list[str] = []
    created_at: datetime


class BillList(ORMModel):
    items: list[BillOut]
