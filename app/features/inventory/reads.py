from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from app.core.constants import (
    ADJUST_REASONS,
    REASON_PURCHASE,
    STOCK_REASONS,
    STOCK_STATUS_LOW,
    STOCK_STATUS_OUT,
    STOCK_SUMMARY_RECENT,
    UNIT_GAZ,
    UNIT_PIECE,
)
from app.core.deps import ShopScope
from app.core.errors import unprocessable
from app.core.money import to_qty
from app.core.time import as_karachi_date, db_day_range
from app.features.inventory.schemas import (
    MovementRow,
    OwnerMovementRow,
    OwnerStockSummary,
    ProductBrief,
    StockSummary,
    TotalsByUnit,
)
from app.features.inventory.service import stock_status_of
from app.models import Bill, Product, StockMovement, User
from app.models.shop import ROLE_OWNER
from app.services.queries import stocks_of


def _movement_base(scope: ShopScope):
    running = func.sum(StockMovement.qty_change).over(
        partition_by=StockMovement.product_id,
        order_by=(StockMovement.created_at.asc(), StockMovement.id.asc()),
        rows=(None, 0),
    )
    return (
        select(
            StockMovement.id.label("id"),
            StockMovement.created_at.label("created_at"),
            StockMovement.product_id.label("product_id"),
            StockMovement.reason.label("reason"),
            StockMovement.adjust_reason.label("adjust_reason"),
            StockMovement.qty_change.label("qty_change"),
            StockMovement.note.label("note"),
            StockMovement.supplier_name.label("supplier_name"),
            StockMovement.ref_id.label("ref_id"),
            StockMovement.created_by.label("created_by"),
            running.label("balance_after"),
        ).where(StockMovement.shop_id == scope.shop_id)
    ).subquery("movement_balances")


def _to_movement(row: dict, owner: bool) -> MovementRow | OwnerMovementRow:
    payload = dict(
        id=row["id"],
        created_at=row["created_at"],
        local_date=as_karachi_date(row["created_at"]),
        product=ProductBrief(
            id=row["product_id"],
            name_ur=row["name_ur"],
            name_en=row["name_en"],
            unit=row["unit"],
        ),
        reason=row["reason"],
        adjust_reason=row["adjust_reason"],
        qty_change=to_qty(row["qty_change"]),
        balance_after=to_qty(row["balance_after"]),
        user_name=row["user_name"],
        supplier_name=row["supplier_name"],
        note=row["note"],
        ref=row["bill_no"],
    )
    if owner:
        return OwnerMovementRow(**payload, unit_cost=row["cost_price"])
    return MovementRow(**payload)


def list_movements(
    scope: ShopScope,
    product_id: UUID | None,
    reason: str | None,
    adjust_reason: str | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
) -> list[MovementRow] | list[OwnerMovementRow]:
    if reason is not None and reason not in STOCK_REASONS:
        raise unprocessable("invalid_reason", "Invalid stock reason")
    if adjust_reason is not None and adjust_reason not in ADJUST_REASONS:
        raise unprocessable("invalid_adjust_reason", "Invalid adjust reason")
    if product_id is not None:
        scope.require(Product, product_id)
    base = _movement_base(scope)
    stmt = (
        select(
            base.c.id,
            base.c.created_at,
            base.c.product_id,
            base.c.reason,
            base.c.adjust_reason,
            base.c.qty_change,
            base.c.note,
            base.c.supplier_name,
            base.c.balance_after,
            Product.name_ur,
            Product.name_en,
            Product.unit,
            Product.cost_price,
            User.name.label("user_name"),
            Bill.bill_no.label("bill_no"),
        )
        .join(Product, Product.id == base.c.product_id)
        .outerjoin(User, User.id == base.c.created_by)
        .outerjoin(Bill, and_(Bill.id == base.c.ref_id, base.c.reason == "sale"))
    )
    if product_id is not None:
        stmt = stmt.where(base.c.product_id == product_id)
    if reason is not None:
        stmt = stmt.where(base.c.reason == reason)
    if adjust_reason is not None:
        stmt = stmt.where(base.c.adjust_reason == adjust_reason)
    if date_from is not None:
        start, _ = db_day_range(scope.db, date_from)
        stmt = stmt.where(base.c.created_at >= start)
    if date_to is not None:
        _, end = db_day_range(scope.db, date_to)
        stmt = stmt.where(base.c.created_at < end)
    stmt = stmt.order_by(base.c.created_at.desc(), base.c.id.desc()).limit(limit).offset(offset)
    owner = scope.user.role == ROLE_OWNER
    return [_to_movement(dict(row), owner) for row in scope.db.execute(stmt).mappings()]


def summary(scope: ShopScope) -> StockSummary | OwnerStockSummary:
    products = list(scope.db.scalars(scope.select(Product).where(Product.is_active.is_(True))))
    stocks = stocks_of(scope, [p.id for p in products])
    gaz = Decimal("0")
    piece = Decimal("0")
    low = 0
    out = 0
    for product in products:
        qty = stocks[product.id]
        status = stock_status_of(qty, to_qty(product.min_stock))
        if status == STOCK_STATUS_LOW:
            low += 1
        elif status == STOCK_STATUS_OUT:
            out += 1
        if product.unit == UNIT_GAZ:
            gaz += qty
        elif product.unit == UNIT_PIECE:
            piece += qty
    recent = list_movements(scope, None, None, None, None, None, STOCK_SUMMARY_RECENT, 0)
    purchases = list_movements(
        scope, None, REASON_PURCHASE, None, None, None, STOCK_SUMMARY_RECENT, 0
    )
    payload = dict(
        total_products=len(products),
        low_stock_count=low,
        out_of_stock_count=out,
        totals_by_unit=TotalsByUnit(gaz=to_qty(gaz), piece=to_qty(piece)),
        recent_movements=recent,
        recent_purchases=purchases,
    )
    if scope.user.role == ROLE_OWNER:
        return OwnerStockSummary(**payload)
    return StockSummary(**payload)
