from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_product


def test_presign_without_r2_is_503(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)

    response = client.post(
        "/api/uploads/presign",
        json={"content_type": "image/webp", "product_id": str(product.id)},
        headers=auth_header(token),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "r2_unavailable"


def test_attach_image_rejects_other_shop_prefix(client: TestClient, db: Session) -> None:
    shop, owner, _ = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, owner.username, OWNER_PASSWORD)

    response = client.post(
        f"/api/products/{product.id}/images",
        json={"key": "shops/00000000-0000-4000-8000-000000000099/products/x.webp"},
        headers=auth_header(token),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_key"
