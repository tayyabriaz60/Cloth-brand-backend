from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_

from app.core.constants import (
    ADJUST_COUNT_CORRECTION,
    REASON_ADJUST,
    REASON_PURCHASE,
    STOCK_STATUS_LOW,
    STOCK_STATUS_OK,
    STOCK_STATUS_OUT,
    STOCK_STATUSES,
    UNITS,
)
from app.core.deps import ShopScope
from app.core.errors import not_found, unprocessable
from app.core.money import to_qty
from app.core.time import as_karachi_date
from app.features.inventory.schemas import (
    AdjustIn,
    CountChanged,
    CountIn,
    CountUnchanged,
    OwnerMovementRow,
    OwnerStockRow,
    ProductBrief,
    PurchaseIn,
    StockHistoryRow,
    StockRow,
)
from app.models import Category, Product, StockMovement
from app.models.shop import ROLE_OWNER
from app.services.queries import stock_of, stocks_of
from app.services.tx import commit


def _is_postgres(scope: ShopScope) -> bool:
    return scope.db.get_bind().dialect.name == "postgresql"


def lock_product(scope: ShopScope, product_id: UUID) -> Product:
    stmt = scope.select(Product).where(Product.id == product_id)
    if _is_postgres(scope):
        stmt = stmt.with_for_update()
    product = scope.db.scalar(stmt)
    if product is None:
        raise not_found()
    return product


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def stock_status_of(qty: Decimal, min_stock: Decimal) -> str:
    if qty <= 0:
        return STOCK_STATUS_OUT
    if qty < min_stock:
        return STOCK_STATUS_LOW
    return STOCK_STATUS_OK


def _to_row(product: Product, qty: Decimal, owner: bool) -> StockRow | OwnerStockRow:
    payload = dict(
        product_id=product.id,
        name_ur=product.name_ur,
        name_en=product.name_en,
        design_no=product.design_no,
        unit=product.unit,
        qty=qty,
        min_stock=to_qty(product.min_stock),
        is_low_stock=qty < to_qty(product.min_stock),
        fabric_type=product.fabric_type,
        color=product.color,
    )
    if owner:
        return OwnerStockRow(**payload, cost_price=product.cost_price)
    return StockRow(**payload)


def list_stock(
    scope: ShopScope,
    q: str | None,
    category_id: UUID | None,
    fabric_type: str | None,
    color: str | None,
    unit: str | None,
    stock_status: str | None,
) -> list[StockRow] | list[OwnerStockRow]:
    if unit is not None and unit not in UNITS:
        raise unprocessable("invalid_unit", "Unit must be gaz or piece")
    if stock_status is not None and stock_status not in STOCK_STATUSES:
        raise unprocessable("invalid_stock_status", "stock_status must be low, out, or ok")
    stmt = scope.select(Product).where(Product.is_active.is_(True)).order_by(Product.name_ur)
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Product.name_ur).like(needle),
                func.lower(func.coalesce(Product.name_en, "")).like(needle),
                func.lower(func.coalesce(Product.design_no, "")).like(needle),
            )
        )
    if category_id is not None:
        scope.require(Category, category_id)
        stmt = stmt.where(Product.category_id == category_id)
    if fabric_type and fabric_type.strip():
        stmt = stmt.where(func.lower(Product.fabric_type) == fabric_type.strip().lower())
    if color and color.strip():
        stmt = stmt.where(func.lower(Product.color) == color.strip().lower())
    if unit is not None:
        stmt = stmt.where(Product.unit == unit)
    products = list(scope.db.scalars(stmt))
    stocks = stocks_of(scope, [p.id for p in products])
    owner = scope.user.role == ROLE_OWNER
    rows: list[StockRow] | list[OwnerStockRow] = []
    for product in products:
        qty = stocks[product.id]
        if stock_status and stock_status_of(qty, to_qty(product.min_stock)) != stock_status:
            continue
        rows.append(_to_row(product, qty, owner))
    return rows


def history(scope: ShopScope, product_id: UUID) -> list[StockHistoryRow]:
    scope.require(Product, product_id)
    rows = scope.db.scalars(
        scope.select(StockMovement)
        .where(StockMovement.product_id == product_id)
        .order_by(StockMovement.created_at.desc())
    )
    return [StockHistoryRow.model_validate(row) for row in rows]


def purchase(scope: ShopScope, body: PurchaseIn) -> StockRow | OwnerStockRow:
    product = lock_product(scope, body.product_id)
    qty = to_qty(body.qty)
    if body.cost_price is not None and scope.user.role == ROLE_OWNER:
        product.cost_price = body.cost_price
    scope.db.add(
        StockMovement(
            shop_id=scope.shop_id,
            product_id=product.id,
            qty_change=qty,
            reason=REASON_PURCHASE,
            created_by=scope.user.id,
            note=_blank(body.note),
            supplier_name=_blank(body.supplier_name),
        )
    )
    commit(scope)
    return _to_row(product, stock_of(scope, product.id), scope.user.role == ROLE_OWNER)


def adjust(scope: ShopScope, body: AdjustIn) -> OwnerStockRow:
    product = lock_product(scope, body.product_id)
    qty_change = to_qty(body.qty_change)
    if qty_change == 0:
        raise unprocessable("qty_change_zero", "Adjustment cannot be zero")
    current = stock_of(scope, product.id)
    resulting = current + qty_change
    if resulting < 0:
        raise unprocessable("insufficient_stock", "Stock cannot go below zero")
    scope.db.add(
        StockMovement(
            shop_id=scope.shop_id,
            product_id=product.id,
            qty_change=qty_change,
            reason=REASON_ADJUST,
            adjust_reason=body.adjust_reason,
            created_by=scope.user.id,
            note=body.note.strip(),
        )
    )
    commit(scope)
    return _to_row(product, stock_of(scope, product.id), True)


def count_stock(scope: ShopScope, body: CountIn) -> CountUnchanged | CountChanged:
    product = lock_product(scope, body.product_id)
    counted = to_qty(body.counted_qty)
    current = stock_of(scope, product.id)
    qty_change = to_qty(counted - current)
    if qty_change == 0:
        return CountUnchanged()
    movement = StockMovement(
        shop_id=scope.shop_id,
        product_id=product.id,
        qty_change=qty_change,
        reason=REASON_ADJUST,
        adjust_reason=ADJUST_COUNT_CORRECTION,
        created_by=scope.user.id,
        note=_blank(body.note),
    )
    scope.db.add(movement)
    commit(scope)
    return CountChanged(
        movement=OwnerMovementRow(
            id=movement.id,
            created_at=movement.created_at,
            local_date=as_karachi_date(movement.created_at),
            product=ProductBrief(
                id=product.id, name_ur=product.name_ur, name_en=product.name_en, unit=product.unit
            ),
            reason=REASON_ADJUST,
            adjust_reason=ADJUST_COUNT_CORRECTION,
            qty_change=qty_change,
            balance_after=counted,
            user_name=scope.user.name,
            supplier_name=None,
            note=movement.note,
            ref=None,
            unit_cost=product.cost_price,
        )
    )
