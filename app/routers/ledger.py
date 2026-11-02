from fastapi import APIRouter, status

from app.core.deps import Scope
from app.schemas.people import LedgerEntryOut, PaymentIn, UdhaarList
from app.services import ledger as ledger_service
from app.services import people as people_service

router = APIRouter(prefix="/api", tags=["udhaar"])


@router.get("/udhaar", response_model=UdhaarList, summary="Customers with unpaid balance")
def list_udhaar(scope: Scope) -> UdhaarList:
    return UdhaarList(items=people_service.list_udhaar(scope))


@router.post(
    "/ledger/payment",
    response_model=LedgerEntryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record an udhaar payment",
)
def record_payment(scope: Scope, body: PaymentIn) -> LedgerEntryOut:
    return ledger_service.record_payment(scope, body)
