import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, ShopOwnedMixin
from app.models.catalog import QTY


class Bill(ShopOwnedMixin, Base):
    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("shop_id", "bill_no"),
        CheckConstraint("bill_no > 0", name="bill_no_positive"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint("discount >= 0 AND discount <= subtotal", name="discount_valid"),
        CheckConstraint("total >= 0", name="total_non_negative"),
        CheckConstraint("paid_amount >= 0", name="paid_amount_non_negative"),
        CheckConstraint("payment_type IN ('cash', 'udhaar', 'online')", name="payment_type_valid"),
        CheckConstraint("customer_lang IN ('ur', 'en')", name="customer_lang_valid"),
        CheckConstraint(
            "payment_type <> 'udhaar' OR customer_id IS NOT NULL", name="udhaar_needs_customer"
        ),
        Index("ix_bills_shop_id_created_at", "shop_id", "created_at"),
    )

    # Client-generated UUID (idempotency key), so no server default.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    bill_no: Mapped[int] = mapped_column(Integer)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    subtotal: Mapped[int] = mapped_column(Integer)
    discount: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total: Mapped[int] = mapped_column(Integer)
    paid_amount: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    payment_type: Mapped[str] = mapped_column(String(10))
    customer_lang: Mapped[str] = mapped_column(String(2), default="ur", server_default="ur")
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    note: Mapped[str | None] = mapped_column(String(300))


class BillItem(ShopOwnedMixin, Base):
    __tablename__ = "bill_items"
    __table_args__ = (
        CheckConstraint("qty > 0", name="qty_positive"),
        CheckConstraint("rate >= 0", name="rate_non_negative"),
        CheckConstraint("line_total >= 0", name="line_total_non_negative"),
        CheckConstraint("unit IN ('gaz', 'piece')", name="unit_valid"),
        Index("ix_bill_items_shop_id_created_at", "shop_id", "created_at"),
    )

    bill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bills.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    name_snapshot: Mapped[str] = mapped_column(String(150))
    qty: Mapped[Decimal] = mapped_column(QTY)
    unit: Mapped[str] = mapped_column(String(10))
    rate: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[int] = mapped_column(Integer)
