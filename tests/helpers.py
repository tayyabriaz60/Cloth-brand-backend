from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Customer, Product, StockMovement
from tests.conftest import auth_header


def add_product(
    db: Session,
    shop_id: UUID,
    *,
    name_ur: str = "لان",
    unit: str = "gaz",
    cost_price: int = 100,
    sale_price: int = 200,
    min_stock: Decimal = Decimal("5"),
    opening: Decimal = Decimal("10"),
    is_active: bool = True,
    fabric_type: str | None = None,
    color: str | None = None,
    category_id: UUID | None = None,
) -> Product:
    product = Product(
        shop_id=shop_id,
        name_ur=name_ur,
        name_en="Lawn",
        design_no="LW-TEST",
        unit=unit,
        cost_price=cost_price,
        sale_price=sale_price,
        min_stock=min_stock,
        is_active=is_active,
        fabric_type=fabric_type,
        color=color,
        category_id=category_id,
    )
    db.add(product)
    db.flush()
    if opening != 0:
        db.add(
            StockMovement(
                shop_id=shop_id, product_id=product.id, qty_change=opening, reason="opening"
            )
        )
    db.commit()
    db.refresh(product)
    return product


def add_customer(db: Session, shop_id: UUID, name: str = "Ahmed") -> Customer:
    customer = Customer(shop_id=shop_id, name=name, phone="03001111111")
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def make_bill_body(
    product_id: UUID,
    *,
    bill_id: UUID | None = None,
    qty: str = "3.5",
    rate: int = 200,
    discount: int = 0,
    discount_type: str = "amount",
    payment_type: str = "cash",
    paid_amount: int | None = None,
    customer_id: UUID | None = None,
) -> dict:
    subtotal = int((Decimal(qty) * Decimal(rate)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if discount_type == "percent":
        disc = int(round(subtotal * discount / 100))
    else:
        disc = discount
    total = subtotal - disc
    paid = total if paid_amount is None else paid_amount
    return {
        "id": str(bill_id or uuid4()),
        "customer_id": str(customer_id) if customer_id else None,
        "items": [{"product_id": str(product_id), "qty": qty, "rate": rate}],
        "discount": discount,
        "discount_type": discount_type,
        "payment_type": payment_type,
        "paid_amount": paid,
        "customer_lang": "ur",
        "note": None,
    }


def post_bill(client: TestClient, token: str, body: dict):
    return client.post("/api/bills", json=body, headers=auth_header(token))
