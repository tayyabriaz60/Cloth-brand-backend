from uuid import UUID

from sqlalchemy import func

from app.core.constants import ENTRY_UDHAAR
from app.core.deps import ShopScope
from app.core.time import as_karachi_date, today_karachi
from app.models import Bill, Customer, LedgerEntry
from app.schemas.people import (
    CustomerOut,
    CustomerPatch,
    CustomerWrite,
    LedgerEntryOut,
    UdhaarRow,
)
from app.services.queries import balance_of
from app.services.tx import commit


def list_customers(scope: ShopScope, q: str | None) -> list[CustomerOut]:
    stmt = scope.select(Customer).order_by(Customer.name)
    if q and q.strip():
        stmt = stmt.where(func.lower(Customer.name).like(f"%{q.strip().lower()}%"))
    rows = list(scope.db.scalars(stmt))
    return [_customer_out(scope, row) for row in rows]


def create_customer(scope: ShopScope, body: CustomerWrite) -> CustomerOut:
    customer = Customer(
        shop_id=scope.shop_id,
        name=body.name.strip(),
        phone=body.phone.strip() if body.phone else None,
        note=body.note,
    )
    scope.db.add(customer)
    commit(scope)
    return _customer_out(scope, customer)


def patch_customer(scope: ShopScope, customer_id: UUID, body: CustomerPatch) -> CustomerOut:
    customer = scope.require(Customer, customer_id)
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(customer, field, value.strip() if isinstance(value, str) and field != "note" else value)
    commit(scope)
    return _customer_out(scope, customer)


def customer_ledger(scope: ShopScope, customer_id: UUID) -> list[LedgerEntryOut]:
    scope.require(Customer, customer_id)
    entries = list(
        scope.db.scalars(
            scope.select(LedgerEntry)
            .where(LedgerEntry.customer_id == customer_id)
            .order_by(LedgerEntry.created_at.desc())
        )
    )
    bill_ids = [e.bill_id for e in entries if e.bill_id]
    bills = {}
    if bill_ids:
        bills = {b.id: b.bill_no for b in scope.db.scalars(scope.select(Bill).where(Bill.id.in_(bill_ids)))}
    return [
        LedgerEntryOut(
            id=e.id,
            entry_type=e.entry_type,
            amount=e.amount,
            bill_id=e.bill_id,
            bill_no=bills.get(e.bill_id) if e.bill_id else None,
            note=e.note,
            created_at=e.created_at,
        )
        for e in entries
    ]


def list_udhaar(scope: ShopScope) -> list[UdhaarRow]:
    customers = list(scope.db.scalars(scope.select(Customer)))
    rows: list[UdhaarRow] = []
    today = today_karachi()
    for customer in customers:
        balance = balance_of(scope, customer.id)
        if balance <= 0:
            continue
        oldest = scope.db.scalar(
            scope.select(LedgerEntry)
            .where(LedgerEntry.customer_id == customer.id, LedgerEntry.entry_type == ENTRY_UDHAAR)
            .order_by(LedgerEntry.created_at.asc())
            .limit(1)
        )
        days = 0
        if oldest is not None:
            days = (today - as_karachi_date(oldest.created_at)).days
        rows.append(
            UdhaarRow(
                customer_id=customer.id,
                name=customer.name,
                phone=customer.phone,
                balance=balance,
                days_since_oldest=days,
            )
        )
    rows.sort(key=lambda r: (-r.days_since_oldest, r.name))
    return rows


def _customer_out(scope: ShopScope, customer: Customer) -> CustomerOut:
    return CustomerOut(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        note=customer.note,
        balance=balance_of(scope, customer.id),
    )
