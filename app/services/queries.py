from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select

from app.core.constants import ENTRY_PAYMENT, ENTRY_UDHAAR
from app.core.deps import ShopScope
from app.core.money import to_qty
from app.models import LedgerEntry, StockMovement


def stock_of(scope: ShopScope, product_id: UUID) -> Decimal:
    total = scope.db.scalar(
        select(func.coalesce(func.sum(StockMovement.qty_change), 0)).where(
            StockMovement.shop_id == scope.shop_id, StockMovement.product_id == product_id
        )
    )
    return to_qty(Decimal(str(total or 0)))


def stocks_of(scope: ShopScope, product_ids: list[UUID]) -> dict[UUID, Decimal]:
    if not product_ids:
        return {}
    rows = scope.db.execute(
        select(StockMovement.product_id, func.coalesce(func.sum(StockMovement.qty_change), 0)).where(
            StockMovement.shop_id == scope.shop_id, StockMovement.product_id.in_(product_ids)
        ).group_by(StockMovement.product_id)
    ).all()
    found = {pid: to_qty(Decimal(str(qty))) for pid, qty in rows}
    return {pid: found.get(pid, to_qty(0)) for pid in product_ids}


def balance_of(scope: ShopScope, customer_id: UUID) -> int:
    total = scope.db.scalar(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.entry_type == ENTRY_UDHAAR, LedgerEntry.amount),
                        (LedgerEntry.entry_type == ENTRY_PAYMENT, -LedgerEntry.amount),
                        else_=0,
                    )
                ),
                0,
            )
        ).where(LedgerEntry.shop_id == scope.shop_id, LedgerEntry.customer_id == customer_id)
    )
    return int(total or 0)
