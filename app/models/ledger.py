import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, ShopOwnedMixin
from app.models.catalog import QTY

REASON_OPENING = "opening"


class StockMovement(ShopOwnedMixin, Base):
    """Stock of a product = SUM(qty_change). Never store stock as a number."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("qty_change <> 0", name="qty_change_non_zero"),
        CheckConstraint(
            "reason IN ('sale', 'purchase', 'return', 'adjust', 'opening')", name="reason_valid"
        ),
        Index("ix_stock_movements_shop_id_created_at", "shop_id", "created_at"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    qty_change: Mapped[Decimal] = mapped_column(QTY)
    reason: Mapped[str] = mapped_column(String(10))
    ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    note: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), index=True)


class LedgerEntry(ShopOwnedMixin, Base):
    """Customer balance = SUM(udhaar) - SUM(payment). Amount is always positive."""

    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("entry_type IN ('udhaar', 'payment')", name="entry_type_valid"),
        Index("ix_ledger_entries_shop_id_created_at", "shop_id", "created_at"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    entry_type: Mapped[str] = mapped_column(String(10))
    amount: Mapped[int] = mapped_column(Integer)
    bill_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("bills.id", ondelete="RESTRICT"), index=True
    )
    note: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), index=True)


class Expense(ShopOwnedMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        Index("ix_expenses_shop_id_created_at", "shop_id", "created_at"),
    )

    title: Mapped[str] = mapped_column(String(150))
    amount: Mapped[int] = mapped_column(Integer)
    expense_date: Mapped[date] = mapped_column(Date)


class SupplierPayment(ShopOwnedMixin, Base):
    __tablename__ = "supplier_payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint("type IN ('bought', 'paid')", name="type_valid"),
        Index("ix_supplier_payments_shop_id_created_at", "shop_id", "created_at"),
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    amount: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(10))
    note: Mapped[str | None] = mapped_column(String(300))
