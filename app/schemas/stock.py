from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, QtyOut


class StockRow(ORMModel):
    product_id: UUID
    name_ur: str
    name_en: str | None
    design_no: str | None
    unit: str
    qty: QtyOut
    min_stock: QtyOut
    is_low_stock: bool


class OwnerStockRow(StockRow):
    cost_price: int


class StockList(ORMModel):
    items: list[StockRow]


class OwnerStockList(ORMModel):
    items: list[OwnerStockRow]


class StockHistoryRow(ORMModel):
    id: UUID
    qty_change: QtyOut
    reason: str
    ref_id: UUID | None
    note: str | None
    created_at: datetime


class StockHistoryList(ORMModel):
    items: list[StockHistoryRow]


class PurchaseIn(ORMModel):
    product_id: UUID
    qty: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    cost_price: int | None = Field(default=None, ge=0)
    supplier_name: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=300)


class AdjustIn(ORMModel):
    product_id: UUID
    qty_change: Decimal = Field(max_digits=10, decimal_places=2)
    note: str = Field(min_length=1, max_length=300)
