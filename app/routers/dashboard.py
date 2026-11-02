from fastapi import APIRouter

from app.core.deps import Scope
from app.schemas.dashboard import CashierDashboard, OwnerDashboard
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", summary="Today's numbers (owner sees sales, cashier does not)")
def dashboard(scope: Scope) -> OwnerDashboard | CashierDashboard:
    return dashboard_service.get_dashboard(scope)
