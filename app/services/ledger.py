from app.core.constants import ENTRY_PAYMENT
from app.core.deps import ShopScope
from app.core.errors import unprocessable
from app.models import Customer, LedgerEntry
from app.schemas.people import LedgerEntryOut, PaymentIn
from app.services.queries import balance_of
from app.services.tx import commit


def record_payment(scope: ShopScope, body: PaymentIn) -> LedgerEntryOut:
    customer = scope.require(Customer, body.customer_id)
    balance = balance_of(scope, customer.id)
    if body.amount > balance:
        raise unprocessable("payment_exceeds_balance", "Payment cannot be greater than the balance")
    entry = LedgerEntry(
        shop_id=scope.shop_id,
        customer_id=customer.id,
        entry_type=ENTRY_PAYMENT,
        amount=body.amount,
        note=body.note,
        created_by=scope.user.id,
    )
    scope.db.add(entry)
    commit(scope)
    return LedgerEntryOut(
        id=entry.id,
        entry_type=entry.entry_type,
        amount=entry.amount,
        bill_id=None,
        bill_no=None,
        note=entry.note,
        created_at=entry.created_at,
    )
