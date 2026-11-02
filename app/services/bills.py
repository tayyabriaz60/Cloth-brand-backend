from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.constants import (
    DISCOUNT_PERCENT,
    DISCOUNT_TYPES,
    ENTRY_UDHAAR,
    LOW_STOCK_WARNING,
    NEGATIVE_STOCK_WARNING,
    PAYMENT_CASH,
    PAYMENT_ONLINE,
    PAYMENT_TYPES,
    PAYMENT_UDHAAR,
    REASON_SALE,
)
from app.core.deps import ShopScope
from app.core.errors import conflict, unprocessable
from app.core.money import percent_of, rupees_from_qty_rate, to_qty
from app.core.time import db_day_range, today_karachi
from app.models import Bill, BillItem, Customer, LedgerEntry, Product, ShopCounter, StockMovement
from app.schemas.sales import BillCreateIn, BillItemOut, BillOut
from app.services.queries import stock_of
from datetime import date
from decimal import Decimal


class _PreparedLine:
    def __init__(self, qty: Decimal, rate: int, line_total: int) -> None:
        self.qty = qty
        self.rate = rate
        self.line_total = line_total


def _bill_out(scope: ShopScope, bill: Bill, warnings: list[str] | None = None) -> BillOut:
    items = list(
        scope.db.scalars(
            scope.select(BillItem).where(BillItem.bill_id == bill.id).order_by(BillItem.created_at)
        )
    )
    return BillOut(
        id=bill.id,
        bill_no=bill.bill_no,
        customer_id=bill.customer_id,
        subtotal=bill.subtotal,
        discount=bill.discount,
        total=bill.total,
        paid_amount=bill.paid_amount,
        payment_type=bill.payment_type,
        customer_lang=bill.customer_lang,
        note=bill.note,
        items=[BillItemOut.model_validate(i) for i in items],
        warnings=warnings or [],
        created_at=bill.created_at,
    )


def get_bill(scope: ShopScope, bill_id: UUID) -> BillOut:
    return _bill_out(scope, scope.require(Bill, bill_id))


def list_bills(scope: ShopScope, day: date | None) -> list[BillOut]:
    start, end = db_day_range(scope.db, day or today_karachi())
    rows = list(
        scope.db.scalars(
            scope.select(Bill)
            .where(Bill.created_at >= start, Bill.created_at < end)
            .order_by(Bill.bill_no)
        )
    )
    return [_bill_out(scope, row) for row in rows]


def _next_bill_no(scope: ShopScope) -> int:
    stmt = select(ShopCounter).where(ShopCounter.shop_id == scope.shop_id)
    if scope.db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    counter = scope.db.scalar(stmt)
    if counter is None:
        counter = ShopCounter(shop_id=scope.shop_id, last_bill_no=0)
        scope.db.add(counter)
        scope.db.flush()
    counter.last_bill_no += 1
    return counter.last_bill_no


def _discount_rupees(subtotal: int, discount: int, discount_type: str) -> int:
    if discount_type not in DISCOUNT_TYPES:
        raise unprocessable("invalid_discount_type", "Discount type must be amount or percent")
    if discount_type == DISCOUNT_PERCENT:
        if discount > 100:
            raise unprocessable("discount_too_high", "Percent discount cannot exceed 100")
        return percent_of(subtotal, discount)
    if discount > subtotal:
        raise unprocessable("discount_too_high", "Discount cannot be greater than the subtotal")
    return discount


def _snapshot_name(product: Product, lang: str) -> str:
    if lang == "en" and product.name_en and product.name_en.strip():
        return product.name_en
    return product.name_ur


def create_bill(scope: ShopScope, body: BillCreateIn) -> tuple[BillOut, bool]:
    existing = scope.get(Bill, body.id)
    if existing is not None:
        return _bill_out(scope, existing), True

    if not body.items:
        raise unprocessable("empty_items", "A bill needs at least one item")
    if body.payment_type not in PAYMENT_TYPES:
        raise unprocessable("invalid_payment_type", "Payment type must be cash, udhaar, or online")
    if body.customer_lang not in ("ur", "en"):
        raise unprocessable("invalid_customer_lang", "Customer language must be ur or en")

    customer = None
    if body.customer_id is not None:
        customer = scope.require(Customer, body.customer_id)
    if body.payment_type == PAYMENT_UDHAAR and customer is None:
        raise unprocessable("udhaar_needs_customer", "Udhaar requires a customer")

    prepared: list[tuple[Product, _PreparedLine]] = []
    subtotal = 0
    warnings: list[str] = []
    for line in body.items:
        product = scope.require(Product, line.product_id)
        if not product.is_active:
            raise unprocessable("inactive_product", "This product is not for sale")
        qty = to_qty(line.qty)
        line_total = rupees_from_qty_rate(qty, line.rate)
        subtotal += line_total
        prepared.append((product, _PreparedLine(qty=qty, rate=line.rate, line_total=line_total)))

    discount = _discount_rupees(subtotal, body.discount, body.discount_type)
    if discount > subtotal:
        raise unprocessable("discount_too_high", "Discount cannot be greater than the subtotal")
    total = subtotal - discount

    if body.payment_type in (PAYMENT_CASH, PAYMENT_ONLINE) and body.paid_amount != total:
        raise unprocessable("invalid_paid_amount", "Cash and online bills must be paid in full")
    if body.payment_type == PAYMENT_UDHAAR and not (0 <= body.paid_amount < total):
        raise unprocessable("invalid_paid_amount", "Udhaar paid amount must be less than the total")

    for product, line in prepared:
        remaining = stock_of(scope, product.id) - line.qty
        if remaining < to_qty(product.min_stock):
            warnings.append(f"{product.name_ur}: {LOW_STOCK_WARNING}")
        if remaining < to_qty(0):
            warnings.append(f"{product.name_ur}: {NEGATIVE_STOCK_WARNING}")

    try:
        bill = Bill(
            id=body.id,
            shop_id=scope.shop_id,
            bill_no=_next_bill_no(scope),
            customer_id=customer.id if customer else None,
            subtotal=subtotal,
            discount=discount,
            total=total,
            paid_amount=body.paid_amount,
            payment_type=body.payment_type,
            customer_lang=body.customer_lang,
            created_by=scope.user.id,
            note=body.note,
        )
        scope.db.add(bill)
        scope.db.flush()
        for product, line in prepared:
            scope.db.add(
                BillItem(
                    shop_id=scope.shop_id,
                    bill_id=bill.id,
                    product_id=product.id,
                    name_snapshot=_snapshot_name(product, body.customer_lang),
                    qty=line.qty,
                    unit=product.unit,
                    rate=line.rate,
                    line_total=line.line_total,
                )
            )
            scope.db.add(
                StockMovement(
                    shop_id=scope.shop_id,
                    product_id=product.id,
                    qty_change=-line.qty,
                    reason=REASON_SALE,
                    ref_id=bill.id,
                    created_by=scope.user.id,
                )
            )
        due = total - body.paid_amount
        if due > 0 and customer is not None:
            scope.db.add(
                LedgerEntry(
                    shop_id=scope.shop_id,
                    customer_id=customer.id,
                    entry_type=ENTRY_UDHAAR,
                    amount=due,
                    bill_id=bill.id,
                    created_by=scope.user.id,
                )
            )
        scope.db.commit()
    except IntegrityError:
        scope.db.rollback()
        again = scope.get(Bill, body.id)
        if again is not None:
            return _bill_out(scope, again), True
        raise conflict("That bill id is already used")

    return _bill_out(scope, bill, warnings), False

