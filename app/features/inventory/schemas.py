from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.core.constants import ADJUST_REASONS, SUPPLIER_NAME_MAX
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
    fabric_type: str | None
    color: str | None


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
    supplier_name: str | None = Field(default=None, max_length=SUPPLIER_NAME_MAX)
    note: str | None = Field(default=None, max_length=300)


class AdjustIn(ORMModel):
    product_id: UUID
    qty_change: Decimal = Field(max_digits=10, decimal_places=2)
    adjust_reason: str
    note: str = Field(min_length=1, max_length=300)

    @field_validator("adjust_reason")
    @classmethod
    def _adjust_reason(cls, value: str) -> str:
        if value not in ADJUST_REASONS:
            raise ValueError("Invalid adjust reason")
        return value


class CountIn(ORMModel):
    product_id: UUID
    counted_qty: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    note: str | None = Field(default=None, max_length=300)


class ProductBrief(ORMModel):
    id: UUID
    name_ur: str
    name_en: str | None
    unit: str


class MovementRow(ORMModel):
    id: UUID
    created_at: datetime
    local_date: date
    product: ProductBrief
    reason: str
    adjust_reason: str | None
    qty_change: QtyOut
    balance_after: QtyOut
    user_name: str | None
    supplier_name: str | None
    note: str | None
    ref: int | None


class OwnerMovementRow(MovementRow):
    unit_cost: int


class MovementList(ORMModel):
    items: list[MovementRow]


class OwnerMovementList(ORMModel):
    items: list[OwnerMovementRow]


class CountUnchanged(ORMModel):
    changed: Literal[False] = False


class CountChanged(ORMModel):
    changed: Literal[True] = True
    movement: OwnerMovementRow


class TotalsByUnit(ORMModel):
    gaz: QtyOut
    piece: QtyOut


class StockSummary(ORMModel):
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    totals_by_unit: TotalsByUnit
    recent_movements: list[MovementRow]
    recent_purchases: list[MovementRow]


class OwnerStockSummary(ORMModel):
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    totals_by_unit: TotalsByUnit
    recent_movements: list[OwnerMovementRow]
    recent_purchases: list[OwnerMovementRow]
