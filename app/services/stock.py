from uuid import UUID

from sqlalchemy import func

from app.core.constants import REASON_ADJUST, REASON_PURCHASE
from app.core.deps import ShopScope
from app.core.errors import unprocessable
from app.core.money import to_qty
from app.models import Product, StockMovement
from app.models.shop import ROLE_OWNER
from app.schemas.stock import AdjustIn, OwnerStockRow, PurchaseIn, StockHistoryRow, StockRow
from app.services.queries import stock_of, stocks_of
from app.services.tx import commit


def list_stock(scope: ShopScope, q: str | None) -> list[StockRow] | list[OwnerStockRow]:
    stmt = scope.select(Product).where(Product.is_active.is_(True)).order_by(Product.name_ur)
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(func.lower(Product.name_ur).like(needle))
    products = list(scope.db.scalars(stmt))
    stocks = stocks_of(scope, [p.id for p in products])
    owner = scope.user.role == ROLE_OWNER
    rows: list[StockRow] | list[OwnerStockRow] = []
    for p in products:
        qty = stocks[p.id]
        base = dict(
            product_id=p.id,
            name_ur=p.name_ur,
            name_en=p.name_en,
            design_no=p.design_no,
            unit=p.unit,
            qty=qty,
            min_stock=to_qty(p.min_stock),
            is_low_stock=qty < to_qty(p.min_stock),
        )
        rows.append(OwnerStockRow(**base, cost_price=p.cost_price) if owner else StockRow(**base))
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
    product = scope.require(Product, body.product_id)
    qty = to_qty(body.qty)
    note = body.note
    if body.supplier_name:
        extra = f"Supplier: {body.supplier_name.strip()}"
        note = f"{extra}. {note}" if note else extra
    if body.cost_price is not None and scope.user.role == ROLE_OWNER:
        product.cost_price = body.cost_price
    scope.db.add(
        StockMovement(
            shop_id=scope.shop_id,
            product_id=product.id,
            qty_change=qty,
            reason=REASON_PURCHASE,
            created_by=scope.user.id,
            note=note,
        )
    )
    commit(scope)
    qty_now = stock_of(scope, product.id)
    row = dict(
        product_id=product.id,
        name_ur=product.name_ur,
        name_en=product.name_en,
        design_no=product.design_no,
        unit=product.unit,
        qty=qty_now,
        min_stock=to_qty(product.min_stock),
        is_low_stock=qty_now < to_qty(product.min_stock),
    )
    if scope.user.role == ROLE_OWNER:
        return OwnerStockRow(**row, cost_price=product.cost_price)
    return StockRow(**row)


def adjust(scope: ShopScope, body: AdjustIn) -> OwnerStockRow:
    product = scope.require(Product, body.product_id)
    qty_change = to_qty(body.qty_change)
    if qty_change == 0:
        raise unprocessable("qty_change_zero", "Adjustment cannot be zero")
    scope.db.add(
        StockMovement(
            shop_id=scope.shop_id,
            product_id=product.id,
            qty_change=qty_change,
            reason=REASON_ADJUST,
            created_by=scope.user.id,
            note=body.note.strip(),
        )
    )
    commit(scope)
    qty_now = stock_of(scope, product.id)
    return OwnerStockRow(
        product_id=product.id,
        name_ur=product.name_ur,
        name_en=product.name_en,
        design_no=product.design_no,
        unit=product.unit,
        qty=qty_now,
        min_stock=to_qty(product.min_stock),
        is_low_stock=qty_now < to_qty(product.min_stock),
        cost_price=product.cost_price,
    )
