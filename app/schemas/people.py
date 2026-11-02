from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel


class CustomerOut(ORMModel):
    id: UUID
    name: str
    phone: str | None
    note: str | None
    balance: int


class CustomerList(ORMModel):
    items: list[CustomerOut]


class CustomerWrite(ORMModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    note: str | None = Field(default=None, max_length=300)


class CustomerPatch(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    note: str | None = Field(default=None, max_length=300)


class LedgerEntryOut(ORMModel):
    id: UUID
    entry_type: str
    amount: int
    bill_id: UUID | None
    bill_no: int | None
    note: str | None
    created_at: datetime


class LedgerList(ORMModel):
    items: list[LedgerEntryOut]


class UdhaarRow(ORMModel):
    customer_id: UUID
    name: str
    phone: str | None
    balance: int
    days_since_oldest: int


class UdhaarList(ORMModel):
    items: list[UdhaarRow]


class PaymentIn(ORMModel):
    customer_id: UUID
    amount: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=300)
