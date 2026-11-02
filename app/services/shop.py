from app.core.constants import PAPER_WIDTHS
from app.core.deps import ShopScope
from app.core.errors import unprocessable
from app.models import Shop
from app.schemas.shop import ShopPatch, ShopPublic
from app.services.tx import commit


def get_shop(scope: ShopScope) -> ShopPublic:
    shop = scope.db.get(Shop, scope.shop_id)
    return ShopPublic.model_validate(shop)


def patch_shop(scope: ShopScope, body: ShopPatch) -> ShopPublic:
    shop = scope.db.get(Shop, scope.shop_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("paper_width") is not None and data["paper_width"] not in PAPER_WIDTHS:
        raise unprocessable("invalid_paper_width", "Paper width must be 58 or 80")
    for field, value in data.items():
        setattr(shop, field, value.strip() if isinstance(value, str) else value)
    commit(scope)
    return ShopPublic.model_validate(shop)
