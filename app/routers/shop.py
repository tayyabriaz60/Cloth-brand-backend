from fastapi import APIRouter

from app.core.deps import OwnerUser, Scope
from app.schemas.shop import ShopPatch, ShopPublic
from app.services import shop as shop_service

router = APIRouter(prefix="/api/shop", tags=["shop"])


@router.get("", response_model=ShopPublic, summary="This shop")
def get_shop(scope: Scope) -> ShopPublic:
    return shop_service.get_shop(scope)


@router.patch("", response_model=ShopPublic, summary="Update shop settings (owner)")
def patch_shop(_owner: OwnerUser, scope: Scope, body: ShopPatch) -> ShopPublic:
    return shop_service.patch_shop(scope, body)
