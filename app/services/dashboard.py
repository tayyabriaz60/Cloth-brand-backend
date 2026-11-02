from datetime import timedelta

from sqlalchemy import func, select

from app.core.constants import DASHBOARD_TOP_N, DASHBOARD_WEEK_DAYS, ENTRY_PAYMENT
from app.core.deps import ShopScope
from app.core.money import to_qty
from app.core.time import db_day_range, today_karachi
from app.models import Bill, LedgerEntry, Product
from app.models.shop import ROLE_OWNER
from app.schemas.dashboard import (
    CashierDashboard,
    LastBillCashier,
    LastBillOwner,
    LowStockItem,
    OwnerDashboard,
    TopUdhaar,
    WeekSale,
)
from app.services.people import list_udhaar
from app.services.queries import stocks_of


def _low_stock(scope: ShopScope) -> list[LowStockItem]:
    products = list(scope.db.scalars(scope.select(Product).where(Product.is_active.is_(True))))
    stocks = stocks_of(scope, [p.id for p in products])
    items = [
        LowStockItem(
            product_id=p.id,
            name_ur=p.name_ur,
            name_en=p.name_en,
            stock=stocks[p.id],
            min_stock=to_qty(p.min_stock),
        )
        for p in products
        if stocks[p.id] < to_qty(p.min_stock)
    ]
    items.sort(key=lambda i: i.stock)
    return items


def get_dashboard(scope: ShopScope) -> OwnerDashboard | CashierDashboard:
    today = today_karachi()
    start, end = db_day_range(scope.db, today)
    udhaar = list_udhaar(scope)
    low = _low_stock(scope)
    last = list(scope.db.scalars(scope.select(Bill).order_by(Bill.created_at.desc()).limit(DASHBOARD_TOP_N)))
    top = [
        TopUdhaar(customer_id=r.customer_id, name=r.name, balance=r.balance)
        for r in sorted(udhaar, key=lambda r: r.balance, reverse=True)[:DASHBOARD_TOP_N]
    ]
    shared = dict(
        total_udhaar=sum(r.balance for r in udhaar),
        low_stock_count=len(low),
        top_udhaar=top,
        low_stock=low[:DASHBOARD_TOP_N],
    )
    if scope.user.role != ROLE_OWNER:
        return CashierDashboard(
            **shared,
            last_bills=[
                LastBillCashier(id=b.id, bill_no=b.bill_no, payment_type=b.payment_type, created_at=b.created_at)
                for b in last
            ],
        )

    today_bills = list(
        scope.db.scalars(scope.select(Bill).where(Bill.created_at >= start, Bill.created_at < end))
    )
    pay_sum = scope.db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.shop_id == scope.shop_id,
            LedgerEntry.entry_type == ENTRY_PAYMENT,
            LedgerEntry.created_at >= start,
            LedgerEntry.created_at < end,
        )
    )
    week: list[WeekSale] = []
    for offset in range(DASHBOARD_WEEK_DAYS - 1, -1, -1):
        day = today - timedelta(days=offset)
        d_start, d_end = db_day_range(scope.db, day)
        day_total = scope.db.scalar(
            select(func.coalesce(func.sum(Bill.total), 0)).where(
                Bill.shop_id == scope.shop_id, Bill.created_at >= d_start, Bill.created_at < d_end
            )
        )
        week.append(WeekSale(date=day, total=int(day_total or 0)))
    return OwnerDashboard(
        **shared,
        today_sales=sum(b.total for b in today_bills),
        today_received=sum(b.paid_amount for b in today_bills) + int(pay_sum or 0),
        last_bills=[
            LastBillOwner(
                id=b.id,
                bill_no=b.bill_no,
                total=b.total,
                paid_amount=b.paid_amount,
                payment_type=b.payment_type,
                created_at=b.created_at,
            )
            for b in last
        ],
        week_sales=week,
    )
