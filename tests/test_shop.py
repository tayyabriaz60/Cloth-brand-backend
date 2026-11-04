from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import CASHIER_PASSWORD, OWNER_PASSWORD, auth_header, login, make_shop


def test_shop_patch_is_owner_only(client: TestClient, db: Session) -> None:
    _shop, owner, cashier = make_shop(db, "Alpha")
    owner_token = login(client, owner.username, OWNER_PASSWORD)
    cashier_token = login(client, cashier.username, CASHIER_PASSWORD)

    cashier_patch = client.patch(
        "/api/shop",
        json={"name_en": "New Name"},
        headers=auth_header(cashier_token),
    )
    owner_patch = client.patch(
        "/api/shop",
        json={"name_en": "New Name"},
        headers=auth_header(owner_token),
    )

    assert cashier_patch.status_code == 403
    assert cashier_patch.json()["code"] == "owner_only"
    assert owner_patch.status_code == 200
    assert owner_patch.json()["name_en"] == "New Name"
