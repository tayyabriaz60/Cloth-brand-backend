"""Idempotent demo data. Run: python -m scripts.seed (safe to run twice)."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Category, Customer, Product, Shop, StockMovement, User
from app.models.catalog import UNIT_GAZ, UNIT_PIECE
from app.models.ledger import REASON_OPENING
from app.models.shop import ROLE_CASHIER, ROLE_OWNER, normalize_username

SHOP_NAME_EN = "Demo Cloth House"
SHOP_NAME_UR = "ڈیمو کلاتھ ہاؤس"

DEMO_USERS = (
    ("Owner", "owner", "owner123", ROLE_OWNER),
    ("Cashier", "cashier", "cashier123", ROLE_CASHIER),
)

CATEGORIES = (
    ("Unstitched", "ان اسٹچڈ"),
    ("Stitched", "اسٹچڈ"),
    ("Dupatta", "دوپٹہ"),
    ("Other", "دوسرا"),
)


@dataclass(frozen=True)
class SeedProduct:
    category_en: str
    name_ur: str
    name_en: str
    design_no: str
    unit: str
    cost_price: int
    sale_price: int
    min_stock: Decimal
    opening_qty: Decimal


PRODUCTS = (
    SeedProduct("Unstitched", "لان پرنٹڈ", "Printed Lawn", "LW-101", UNIT_GAZ, 380, 480, Decimal("20"), Decimal("120.5")),
    SeedProduct("Unstitched", "کاٹن سادہ", "Plain Cotton", "CT-205", UNIT_GAZ, 300, 390, Decimal("25"), Decimal("150")),
    SeedProduct("Unstitched", "واش اینڈ ویئر", "Wash & Wear", "WW-310", UNIT_GAZ, 420, 550, Decimal("20"), Decimal("90")),
    SeedProduct("Unstitched", "کھدر", "Khaddar", "KH-402", UNIT_GAZ, 450, 600, Decimal("15"), Decimal("75.5")),
    SeedProduct("Unstitched", "شیفون", "Chiffon", "CH-118", UNIT_GAZ, 520, 700, Decimal("10"), Decimal("60")),
    SeedProduct("Unstitched", "لینن", "Linen", "LN-220", UNIT_GAZ, 480, 640, Decimal("15"), Decimal("80")),
    SeedProduct("Stitched", "کڑھائی والا سوٹ", "Embroidered Suit", "ST-501", UNIT_PIECE, 2800, 3600, Decimal("3"), Decimal("12")),
    SeedProduct("Stitched", "ریڈی میڈ کرتا", "Ready-made Kurta", "ST-512", UNIT_PIECE, 1400, 1900, Decimal("5"), Decimal("20")),
    SeedProduct("Dupatta", "شیفون دوپٹہ", "Chiffon Dupatta", "DP-031", UNIT_PIECE, 450, 650, Decimal("5"), Decimal("25")),
    SeedProduct("Dupatta", "جامہ وار دوپٹہ", "Jamawar Dupatta", "DP-044", UNIT_PIECE, 900, 1250, Decimal("3"), Decimal("10")),
    SeedProduct("Other", "شال", "Shawl", "OT-007", UNIT_PIECE, 1600, 2200, Decimal("2"), Decimal("8")),
    SeedProduct("Other", "لائننگ کپڑا", "Lining Cloth", "OT-015", UNIT_GAZ, 120, 180, Decimal("30"), Decimal("200")),
)

CUSTOMERS = (
    ("Ahmed Raza", "03001234567", "Regular customer"),
    ("Fatima Bibi", "03211234567", None),
    ("Bilal Tailors", "03331234567", "Tailor shop, buys in bulk"),
)


def _get_or_create_shop(db: Session) -> Shop:
    shop = db.scalar(select(Shop).where(Shop.name_en == SHOP_NAME_EN))
    if shop is None:
        shop = Shop(name_ur=SHOP_NAME_UR, name_en=SHOP_NAME_EN, footer_text="شکریہ! دوبارہ تشریف لائیں")
        db.add(shop)
        db.flush()
    return shop


def _seed_users(db: Session, shop: Shop) -> int:
    created = 0
    for name, raw_username, password, role in DEMO_USERS:
        username = normalize_username(raw_username)
        # Usernames are global, so check every shop, not just this one.
        exists = db.scalar(select(User).where(User.username == username))
        if exists is None:
            db.add(
                User(
                    shop_id=shop.id,
                    name=name,
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
            created += 1
    return created


def _seed_categories(db: Session, shop: Shop) -> dict[str, Category]:
    by_name: dict[str, Category] = {}
    for order, (name_en, name_ur) in enumerate(CATEGORIES):
        category = db.scalar(
            select(Category).where(Category.shop_id == shop.id, Category.name_en == name_en)
        )
        if category is None:
            category = Category(shop_id=shop.id, name_en=name_en, name_ur=name_ur, sort_order=order)
            db.add(category)
            db.flush()
        by_name[name_en] = category
    return by_name


def _seed_products(db: Session, shop: Shop, categories: dict[str, Category]) -> int:
    created = 0
    for item in PRODUCTS:
        product = db.scalar(
            select(Product).where(Product.shop_id == shop.id, Product.design_no == item.design_no)
        )
        if product is None:
            product = Product(
                shop_id=shop.id,
                category_id=categories[item.category_en].id,
                name_ur=item.name_ur,
                name_en=item.name_en,
                design_no=item.design_no,
                unit=item.unit,
                cost_price=item.cost_price,
                sale_price=item.sale_price,
                min_stock=item.min_stock,
            )
            db.add(product)
            db.flush()
            created += 1
        has_opening = db.scalar(
            select(StockMovement.id).where(
                StockMovement.product_id == product.id, StockMovement.reason == REASON_OPENING
            )
        )
        if has_opening is None:
            db.add(
                StockMovement(
                    shop_id=shop.id,
                    product_id=product.id,
                    qty_change=item.opening_qty,
                    reason=REASON_OPENING,
                    note="Opening stock (seed)",
                )
            )
    return created


def _seed_customers(db: Session, shop: Shop) -> int:
    created = 0
    for name, phone, note in CUSTOMERS:
        exists = db.scalar(
            select(Customer).where(Customer.shop_id == shop.id, Customer.phone == phone)
        )
        if exists is None:
            db.add(Customer(shop_id=shop.id, name=name, phone=phone, note=note))
            created += 1
    return created


def main() -> None:
    with SessionLocal() as db, db.begin():
        shop = _get_or_create_shop(db)
        users = _seed_users(db, shop)
        categories = _seed_categories(db, shop)
        products = _seed_products(db, shop, categories)
        customers = _seed_customers(db, shop)

    print(f"Seed done. New users: {users}, products: {products}, customers: {customers}.")
    print("=" * 64)
    print("WARNING: demo logins owner/owner123 and cashier/cashier123")
    print("WARNING: CHANGE THESE PASSWORDS before real use!")
    print("=" * 64)


if __name__ == "__main__":
    main()
