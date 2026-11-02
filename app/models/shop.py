import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, ShopOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin

DEFAULT_PAPER_WIDTH = 80
ROLE_OWNER = "owner"
ROLE_CASHIER = "cashier"


def normalize_username(username: str) -> str:
    """Usernames are globally unique and stored lower-case."""
    return username.strip().lower()

JsonType = JSON().with_variant(JSONB(), "postgresql")


class Shop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shops"
    __table_args__ = (CheckConstraint("paper_width IN (58, 80)", name="paper_width_valid"),)

    name_ur: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(30))
    footer_text: Mapped[str | None] = mapped_column(String(300))
    paper_width: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_PAPER_WIDTH, server_default=str(DEFAULT_PAPER_WIDTH)
    )
    auto_print: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    settings: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, server_default="{}")


class User(ShopOwnedMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'cashier')", name="role_valid"),
        CheckConstraint("username = lower(username)", name="username_lowercase"),
        UniqueConstraint("username"),
        Index("ix_users_shop_id_created_at", "shop_id", "created_at"),
    )

    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class ShopCounter(TimestampMixin, Base):
    __tablename__ = "shop_counters"
    __table_args__ = (CheckConstraint("last_bill_no >= 0", name="last_bill_no_non_negative"),)

    shop_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("shops.id", ondelete="CASCADE"), primary_key=True
    )
    last_bill_no: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
