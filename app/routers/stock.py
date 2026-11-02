from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import OwnerUser, Scope
from app.schemas.stock import (
    AdjustIn,
    OwnerStockList,
    OwnerStockRow,
    PurchaseIn,
    StockHistoryList,
    StockList,
    StockRow,
)
from app.services import stock as stock_service

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("", summary="Stock for every active product")
def list_stock(scope: Scope, q: str | None = None) -> OwnerStockList | StockList:
    items = stock_service.list_stock(scope, q)
    if scope.user.role == "owner":
        return OwnerStockList(items=items)  # type: ignore[arg-type]
    return StockList(items=items)  # type: ignore[arg-type]


@router.get("/{product_id}/history", response_model=StockHistoryList, summary="Stock movements")
def history(scope: Scope, product_id: UUID) -> StockHistoryList:
    return StockHistoryList(items=stock_service.history(scope, product_id))


@router.post("/purchase", status_code=status.HTTP_201_CREATED, summary="Record a purchase")
def purchase(scope: Scope, body: PurchaseIn) -> StockRow | OwnerStockRow:
    return stock_service.purchase(scope, body)


@router.post("/adjust", status_code=status.HTTP_201_CREATED, summary="Adjust stock (owner)")
def adjust(_owner: OwnerUser, scope: Scope, body: AdjustIn) -> OwnerStockRow:
    return stock_service.adjust(scope, body)
