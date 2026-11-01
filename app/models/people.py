from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, ShopOwnedMixin


class Customer(ShopOwnedMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (Index("ix_customers_shop_id_created_at", "shop_id", "created_at"),)

    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(300))


class Supplier(ShopOwnedMixin, Base):
    __tablename__ = "suppliers"
    __table_args__ = (Index("ix_suppliers_shop_id_created_at", "shop_id", "created_at"),)

    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
