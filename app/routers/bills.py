from datetime import date
from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.deps import Scope
from app.schemas.sales import BillCreateIn, BillList, BillOut
from app.services import bills as bills_service

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.post("", response_model=BillOut, summary="Create a bill (idempotent on id)")
def create_bill(scope: Scope, body: BillCreateIn, response: Response) -> BillOut:
    bill, existed = bills_service.create_bill(scope, body)
    response.status_code = status.HTTP_200_OK if existed else status.HTTP_201_CREATED
    return bill


@router.get("", response_model=BillList, summary="Bills for a Karachi calendar day")
def list_bills(scope: Scope, date: date | None = None) -> BillList:
    return BillList(items=bills_service.list_bills(scope, date))


@router.get("/{bill_id}", response_model=BillOut, summary="One bill")
def get_bill(scope: Scope, bill_id: UUID) -> BillOut:
    return bills_service.get_bill(scope, bill_id)
