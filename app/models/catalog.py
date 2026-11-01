import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, ShopOwnedMixin

UNIT_GAZ = "gaz"
UNIT_PIECE = "piece"
MAX_IMAGES_PER_PRODUCT = 3

QTY = Numeric(10, 2)


class Category(ShopOwnedMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (Index("ix_categories_shop_id_created_at", "shop_id", "created_at"),)

    name_ur: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str | None] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Product(ShopOwnedMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit IN ('gaz', 'piece')", name="unit_valid"),
        CheckConstraint("cost_price >= 0", name="cost_price_non_negative"),
        CheckConstraint("sale_price >= 0", name="sale_price_non_negative"),
        CheckConstraint("min_stock >= 0", name="min_stock_non_negative"),
        Index("ix_products_shop_id_created_at", "shop_id", "created_at"),
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    name_ur: Mapped[str] = mapped_column(String(150))
    name_en: Mapped[str | None] = mapped_column(String(150))
    design_no: Mapped[str | None] = mapped_column(String(50))
    unit: Mapped[str] = mapped_column(String(10))
    cost_price: Mapped[int] = mapped_column(Integer)
    sale_price: Mapped[int] = mapped_column(Integer)
    min_stock: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    image_key: Mapped[str | None] = mapped_column(String(300))


class ProductImage(ShopOwnedMixin, Base):
    """Max MAX_IMAGES_PER_PRODUCT per product, enforced in the service layer."""

    __tablename__ = "product_images"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        Index("ix_product_images_shop_id_created_at", "shop_id", "created_at"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    r2_key: Mapped[str] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
