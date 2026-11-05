from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.constants import MOVEMENTS_DEFAULT_LIMIT, MOVEMENTS_MAX_LIMIT
from app.core.deps import OwnerUser, Scope
from app.features.inventory import reads, service
from app.features.inventory.schemas import (
    AdjustIn,
    CountChanged,
    CountIn,
    CountUnchanged,
    MovementList,
    OwnerMovementList,
    OwnerStockList,
    OwnerStockRow,
    OwnerStockSummary,
    PurchaseIn,
    StockHistoryList,
    StockList,
    StockRow,
    StockSummary,
)

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("", summary="Stock for every active product")
def list_stock(
    scope: Scope,
    q: str | None = None,
    category_id: UUID | None = None,
    fabric_type: str | None = None,
    color: str | None = None,
    unit: str | None = None,
    stock_status: str | None = None,
) -> OwnerStockList | StockList:
    items = service.list_stock(scope, q, category_id, fabric_type, color, unit, stock_status)
    if scope.user.role == "owner":
        return OwnerStockList(items=items)  # type: ignore[arg-type]
    return StockList(items=items)  # type: ignore[arg-type]


@router.get("/summary", summary="Inventory totals")
def stock_summary(scope: Scope) -> OwnerStockSummary | StockSummary:
    return reads.summary(scope)


@router.get("/movements", summary="Stock movement ledger")
def list_movements(
    scope: Scope,
    product_id: UUID | None = None,
    reason: str | None = None,
    adjust_reason: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=MOVEMENTS_DEFAULT_LIMIT, ge=1, le=MOVEMENTS_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> OwnerMovementList | MovementList:
    items = reads.list_movements(
        scope, product_id, reason, adjust_reason, date_from, date_to, limit, offset
    )
    if scope.user.role == "owner":
        return OwnerMovementList(items=items)  # type: ignore[arg-type]
    return MovementList(items=items)  # type: ignore[arg-type]


@router.post("/purchase", status_code=status.HTTP_201_CREATED, summary="Record a purchase")
def purchase(scope: Scope, body: PurchaseIn) -> StockRow | OwnerStockRow:
    return service.purchase(scope, body)


@router.post("/adjust", status_code=status.HTTP_201_CREATED, summary="Adjust stock (owner)")
def adjust(_owner: OwnerUser, scope: Scope, body: AdjustIn) -> OwnerStockRow:
    return service.adjust(scope, body)


@router.post("/count", summary="Physical stock count (owner)")
def count_stock(_owner: OwnerUser, scope: Scope, body: CountIn) -> CountUnchanged | CountChanged:
    return service.count_stock(scope, body)


@router.get("/{product_id}/history", response_model=StockHistoryList, summary="Stock movements")
def history(scope: Scope, product_id: UUID) -> StockHistoryList:
    return StockHistoryList(items=service.history(scope, product_id))
