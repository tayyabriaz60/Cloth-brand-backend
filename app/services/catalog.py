from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_

from app.core.constants import REASON_OPENING, UNITS
from app.core.deps import ShopScope
from app.core.errors import unprocessable
from app.core.money import to_qty
from app.models import Category, Product, ProductImage, StockMovement
from app.models.shop import ROLE_OWNER
from app.schemas.catalog import (
    CategoryOut,
    CategoryRef,
    ImageOut,
    OwnerProductOut,
    ProductOut,
    ProductPatch,
    ProductWrite,
)
from app.services.queries import stock_of, stocks_of
from app.services.tx import commit
from app.services.uploads import public_url_for


def list_categories(scope: ShopScope) -> list[CategoryOut]:
    rows = scope.db.scalars(scope.select(Category).order_by(Category.sort_order, Category.name_ur)).all()
    return [CategoryOut.model_validate(row) for row in rows]


def _product_query(scope: ShopScope, q: str | None, category_id: UUID | None, include_inactive: bool):
    stmt = scope.select(Product)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    if category_id is not None:
        scope.require(Category, category_id)
        stmt = stmt.where(Product.category_id == category_id)
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Product.name_ur).like(needle),
                func.lower(func.coalesce(Product.name_en, "")).like(needle),
                func.lower(func.coalesce(Product.design_no, "")).like(needle),
            )
        )
    return stmt.order_by(Product.name_ur)


def _images_map(scope: ShopScope, product_ids: list[UUID]) -> dict[UUID, list[ImageOut]]:
    grouped: dict[UUID, list[ImageOut]] = {pid: [] for pid in product_ids}
    if not product_ids:
        return grouped
    rows = scope.db.scalars(
        scope.select(ProductImage)
        .where(ProductImage.product_id.in_(product_ids))
        .order_by(ProductImage.sort_order, ProductImage.created_at)
    ).all()
    for img in rows:
        grouped.setdefault(img.product_id, []).append(
            ImageOut(id=img.id, public_url=public_url_for(img.r2_key), sort_order=img.sort_order)
        )
    return grouped


def _categories_map(scope: ShopScope, category_ids: list[UUID]) -> dict[UUID, CategoryRef]:
    if not category_ids:
        return {}
    rows = scope.db.scalars(scope.select(Category).where(Category.id.in_(category_ids))).all()
    return {c.id: CategoryRef(id=c.id, name_ur=c.name_ur, name_en=c.name_en) for c in rows}


def serialize_product(
    product: Product, stock: Decimal, images: list[ImageOut], category: CategoryRef | None, owner: bool
) -> ProductOut | OwnerProductOut:
    payload = dict(
        id=product.id,
        name_ur=product.name_ur,
        name_en=product.name_en,
        design_no=product.design_no,
        unit=product.unit,
        sale_price=product.sale_price,
        min_stock=to_qty(product.min_stock),
        category=category,
        images=images,
        stock=stock,
        is_low_stock=stock < to_qty(product.min_stock),
        is_active=product.is_active,
        fabric_type=product.fabric_type,
        color=product.color,
    )
    if owner:
        return OwnerProductOut(**payload, cost_price=product.cost_price)
    return ProductOut(**payload)


def list_products(
    scope: ShopScope, q: str | None, category_id: UUID | None, include_inactive: bool
) -> list[ProductOut] | list[OwnerProductOut]:
    products = list(scope.db.scalars(_product_query(scope, q, category_id, include_inactive)))
    ids = [p.id for p in products]
    stocks = stocks_of(scope, ids)
    images = _images_map(scope, ids)
    cats = _categories_map(scope, [p.category_id for p in products if p.category_id])
    owner = scope.user.role == ROLE_OWNER
    return [
        serialize_product(p, stocks[p.id], images[p.id], cats.get(p.category_id) if p.category_id else None, owner)
        for p in products
    ]


def _require_unit(unit: str) -> str:
    if unit not in UNITS:
        raise unprocessable("invalid_unit", "Unit must be gaz or piece")
    return unit


def _require_category(scope: ShopScope, category_id: UUID | None) -> UUID | None:
    if category_id is None:
        return None
    scope.require(Category, category_id)
    return category_id


def create_product(scope: ShopScope, body: ProductWrite) -> OwnerProductOut:
    product = Product(
        shop_id=scope.shop_id,
        category_id=_require_category(scope, body.category_id),
        name_ur=body.name_ur.strip(),
        name_en=body.name_en.strip() if body.name_en else None,
        design_no=body.design_no.strip() if body.design_no else None,
        unit=_require_unit(body.unit),
        cost_price=body.cost_price,
        sale_price=body.sale_price,
        min_stock=to_qty(body.min_stock),
        is_active=body.is_active,
        fabric_type=(body.fabric_type.strip() or None) if body.fabric_type else None,
        color=(body.color.strip() or None) if body.color else None,
    )
    scope.db.add(product)
    scope.db.flush()
    if body.opening_stock is not None:
        scope.db.add(
            StockMovement(
                shop_id=scope.shop_id,
                product_id=product.id,
                qty_change=to_qty(body.opening_stock),
                reason=REASON_OPENING,
                created_by=scope.user.id,
                note="Opening stock",
            )
        )
    commit(scope)
    return get_product(scope, product.id)


def patch_product(scope: ShopScope, product_id: UUID, body: ProductPatch) -> OwnerProductOut:
    product = scope.require(Product, product_id)
    data = body.model_dump(exclude_unset=True)
    if "unit" in data and data["unit"] is not None:
        data["unit"] = _require_unit(data["unit"])
    if "category_id" in data:
        data["category_id"] = _require_category(scope, data["category_id"])
    if "min_stock" in data and data["min_stock"] is not None:
        data["min_stock"] = to_qty(data["min_stock"])
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(product, field, value)
    commit(scope)
    return get_product(scope, product.id)


def get_product(scope: ShopScope, product_id: UUID) -> OwnerProductOut | ProductOut:
    product = scope.require(Product, product_id)
    owner = scope.user.role == ROLE_OWNER
    images = _images_map(scope, [product.id])[product.id]
    cats = _categories_map(scope, [product.category_id] if product.category_id else [])
    return serialize_product(
        product,
        stock_of(scope, product.id),
        images,
        cats.get(product.category_id) if product.category_id else None,
        owner,
    )
