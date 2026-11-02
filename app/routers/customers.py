from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import Scope
from app.schemas.people import CustomerList, CustomerOut, CustomerPatch, CustomerWrite, LedgerList
from app.services import people as people_service

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=CustomerList, summary="List customers with balances")
def list_customers(scope: Scope, q: str | None = None) -> CustomerList:
    return CustomerList(items=people_service.list_customers(scope, q))


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED, summary="Create a customer")
def create_customer(scope: Scope, body: CustomerWrite) -> CustomerOut:
    return people_service.create_customer(scope, body)


@router.patch("/{customer_id}", response_model=CustomerOut, summary="Update a customer")
def patch_customer(scope: Scope, customer_id: UUID, body: CustomerPatch) -> CustomerOut:
    return people_service.patch_customer(scope, customer_id, body)


@router.get("/{customer_id}/ledger", response_model=LedgerList, summary="Customer ledger, newest first")
def customer_ledger(scope: Scope, customer_id: UUID) -> LedgerList:
    return LedgerList(items=people_service.customer_ledger(scope, customer_id))
