from datetime import date, datetime
from uuid import UUID

from app.schemas.common import ORMModel, QtyOut


class TopUdhaar(ORMModel):
    customer_id: UUID
    name: str
    balance: int


class LowStockItem(ORMModel):
    product_id: UUID
    name_ur: str
    name_en: str | None
    stock: QtyOut
    min_stock: QtyOut


class LastBillOwner(ORMModel):
    id: UUID
    bill_no: int
    total: int
    paid_amount: int
    payment_type: str
    created_at: datetime


class LastBillCashier(ORMModel):
    id: UUID
    bill_no: int
    payment_type: str
    created_at: datetime


class WeekSale(ORMModel):
    date: date
    total: int


class OwnerDashboard(ORMModel):
    today_sales: int
    today_received: int
    total_udhaar: int
    low_stock_count: int
    top_udhaar: list[TopUdhaar]
    low_stock: list[LowStockItem]
    last_bills: list[LastBillOwner]
    week_sales: list[WeekSale]


class CashierDashboard(ORMModel):
    total_udhaar: int
    low_stock_count: int
    top_udhaar: list[TopUdhaar]
    low_stock: list[LowStockItem]
    last_bills: list[LastBillCashier]
