from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.constants import IMAGE_WEBP, PRESIGN_TTL_SECONDS
from app.services.uploads import r2_client
from tests.conftest import CASHIER_PASSWORD, OWNER_PASSWORD, auth_header, login, make_shop
from tests.helpers import add_product

FAKE_R2_ACCOUNT = "testaccount"
FAKE_R2_ACCESS_KEY = "AKIATESTFAKEKEY"
FAKE_R2_SECRET_KEY = "testsecretkeytestsecretkey123456"
FAKE_R2_BUCKET = "test-bucket"
FAKE_R2_KEY = "shops/00000000-0000-4000-8000-000000000001/products/x.webp"


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


def test_cashier_cannot_use_upload_routes(client: TestClient, db: Session) -> None:
    shop, _, cashier = make_shop(db, "Alpha")
    product = add_product(db, shop.id)
    token = login(client, cashier.username, CASHIER_PASSWORD)
    headers = auth_header(token)

    presign = client.post(
        "/api/uploads/presign",
        json={"content_type": "image/webp", "product_id": str(product.id)},
        headers=headers,
    )
    attach = client.post(
        f"/api/products/{product.id}/images",
        json={"key": f"shops/{shop.id}/products/x.webp"},
        headers=headers,
    )
    delete = client.delete(f"/api/product-images/{uuid4()}", headers=headers)

    assert presign.status_code == 403
    assert presign.json()["code"] == "owner_only"
    assert attach.status_code == 403
    assert attach.json()["code"] == "owner_only"
    assert delete.status_code == 403
    assert delete.json()["code"] == "owner_only"


def test_presigned_put_url_omits_checksum_and_signs_content_type() -> None:
    client = r2_client(FAKE_R2_ACCOUNT, FAKE_R2_ACCESS_KEY, FAKE_R2_SECRET_KEY)
    url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": FAKE_R2_BUCKET, "Key": FAKE_R2_KEY, "ContentType": IMAGE_WEBP},
        ExpiresIn=PRESIGN_TTL_SECONDS,
    )
    lower = url.lower()
    query = {key.lower(): values for key, values in parse_qs(urlparse(url).query).items()}
    signed_headers = query.get("x-amz-signedheaders", [""])[0]

    assert "x-amz-checksum" not in lower
    assert "x-amz-sdk-checksum-algorithm" not in lower
    assert "x-amz-signature" in query
    assert "content-type" in signed_headers
