from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Category
from tests.conftest import OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_product


def _category(db: Session, shop_id, name_en: str = "Cloth") -> Category:
    row = Category(shop_id=shop_id, name_ur="کپڑا", name_en=name_en)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_stock_filters_status_fabric_color(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    cat = _category(db, shop.id)
    add_product(
        db,
        shop.id,
        name_ur="Lawn",
        opening=Decimal("10"),
        min_stock=Decimal("20"),
        fabric_type="cotton",
        color="blue",
        category_id=cat.id,
    )
    add_product(
        db,
        shop.id,
        name_ur="Shirt",
        unit="piece",
        opening=Decimal("0"),
        min_stock=Decimal("2"),
        fabric_type="linen",
        color="white",
    )
    add_product(
        db,
        shop.id,
        name_ur="OkCotton",
        opening=Decimal("50"),
        min_stock=Decimal("5"),
        fabric_type="cotton",
        color="red",
        category_id=cat.id,
    )
    token = login(client, owner.username, OWNER_PASSWORD)
    headers = auth_header(token)

    low = client.get("/api/stock?stock_status=low", headers=headers)
    out = client.get("/api/stock?stock_status=out", headers=headers)
    ok = client.get("/api/stock?stock_status=ok", headers=headers)
    fabric = client.get("/api/stock?fabric_type=cotton", headers=headers)
    color = client.get("/api/stock?color=blue", headers=headers)
    unit = client.get("/api/stock?unit=piece", headers=headers)
    search = client.get("/api/stock?q=LW-TEST", headers=headers)
    by_cat = client.get(f"/api/stock?category_id={cat.id}", headers=headers)
    summary = client.get("/api/stock/summary", headers=headers)

    assert [i["name_ur"] for i in low.json()["items"]] == ["Lawn"]
    assert [i["name_ur"] for i in out.json()["items"]] == ["Shirt"]
    assert [i["name_ur"] for i in ok.json()["items"]] == ["OkCotton"]
    assert {i["name_ur"] for i in fabric.json()["items"]} == {"Lawn", "OkCotton"}
    assert [i["name_ur"] for i in color.json()["items"]] == ["Lawn"]
    assert [i["name_ur"] for i in unit.json()["items"]] == ["Shirt"]
    assert len(search.json()["items"]) == 3
    assert {i["name_ur"] for i in by_cat.json()["items"]} == {"Lawn", "OkCotton"}
    body = summary.json()
    assert body["total_products"] == 3
    assert body["low_stock_count"] == 1
    assert body["out_of_stock_count"] == 1
    assert body["totals_by_unit"] == {"gaz": "60.00", "piece": "0.00"}
    assert body["recent_purchases"] == []
    assert "unit_cost" in body["recent_movements"][0]


def test_movements_filters_and_pagination(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id, opening=Decimal("10"))
    other = add_product(db, shop.id, name_ur="Other", opening=Decimal("4"))
    token = login(client, owner.username, OWNER_PASSWORD)
    headers = auth_header(token)
    client.post(
        "/api/stock/purchase",
        json={"product_id": str(product.id), "qty": "2", "note": "in"},
        headers=headers,
    )
    client.post(
        "/api/stock/adjust",
        json={
            "product_id": str(product.id),
            "qty_change": "-1",
            "adjust_reason": "damaged",
            "note": "torn",
        },
        headers=headers,
    )

    first = client.get("/api/stock/movements?limit=2&offset=0", headers=headers)
    second = client.get("/api/stock/movements?limit=2&offset=2", headers=headers)
    damaged = client.get("/api/stock/movements?adjust_reason=damaged", headers=headers)
    purchases = client.get("/api/stock/movements?reason=purchase", headers=headers)
    only_product = client.get(f"/api/stock/movements?product_id={product.id}", headers=headers)
    today = first.json()["items"][0]["local_date"]
    by_date = client.get(f"/api/stock/movements?date_from={today}&date_to={today}", headers=headers)

    assert len(first.json()["items"]) == 2
    assert len(second.json()["items"]) == 2
    ids = {row["id"] for row in first.json()["items"]} | {row["id"] for row in second.json()["items"]}
    assert len(ids) == 4
    assert len(damaged.json()["items"]) == 1
    assert damaged.json()["items"][0]["adjust_reason"] == "damaged"
    assert all(row["reason"] == "purchase" for row in purchases.json()["items"])
    assert all(row["product"]["id"] == str(product.id) for row in only_product.json()["items"])
    assert len(only_product.json()["items"]) == 3
    assert len(by_date.json()["items"]) == 4
    assert all(row["product"]["id"] != str(other.id) for row in only_product.json()["items"])


def test_cross_shop_stock_ids_are_404(client: TestClient, db: Session) -> None:
    shop_a, owner_a, _ = make_shop(db, "Alpha")
    shop_b, _, _ = make_shop(db, "Beta")
    product_b = add_product(db, shop_b.id)
    token = login(client, owner_a.username, OWNER_PASSWORD)
    headers = auth_header(token)
    foreign = str(product_b.id)

    purchase = client.post("/api/stock/purchase", json={"product_id": foreign, "qty": "1"}, headers=headers)
    adjust = client.post(
        "/api/stock/adjust",
        json={"product_id": foreign, "qty_change": "-1", "adjust_reason": "damaged", "note": "x"},
        headers=headers,
    )
    count = client.post("/api/stock/count", json={"product_id": foreign, "counted_qty": "1"}, headers=headers)
    history = client.get(f"/api/stock/movements?product_id={foreign}", headers=headers)
    missing = client.get(f"/api/stock/movements?product_id={uuid4()}", headers=headers)

    assert purchase.status_code == 404
    assert adjust.status_code == 404
    assert count.status_code == 404
    assert history.status_code == 404
    assert missing.status_code == 404
    assert purchase.json()["code"] == "not_found"


def test_owner_can_set_fabric_type_and_color(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    token = login(client, owner.username, OWNER_PASSWORD)
    headers = auth_header(token)

    created = client.post(
        "/api/products",
        json={
            "name_ur": "ململ",
            "unit": "gaz",
            "cost_price": 380,
            "sale_price": 480,
            "fabric_type": "cotton",
            "color": "white",
        },
        headers=headers,
    )
    patched = client.patch(
        f"/api/products/{created.json()['id']}",
        json={"color": "blue"},
        headers=headers,
    )

    assert created.status_code == 201
    assert created.json()["fabric_type"] == "cotton"
    assert created.json()["color"] == "white"
    assert patched.json()["color"] == "blue"
    assert patched.json()["fabric_type"] == "cotton"
