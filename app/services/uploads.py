import uuid
from uuid import UUID

import boto3
from fastapi import status

from app.core.config import get_settings
from app.core.constants import ALLOWED_IMAGE_TYPES, PRESIGN_TTL_SECONDS, R2_KEY_PREFIX
from app.core.deps import ShopScope
from app.core.errors import AppError, unprocessable
from app.models import Product, ProductImage
from app.models.catalog import MAX_IMAGES_PER_PRODUCT
from app.schemas.catalog import AttachImageIn, ImageOut
from app.schemas.uploads import PresignIn, PresignOut
from app.services.tx import commit


def public_url_for(key: str) -> str | None:
    base = get_settings().r2_public_base_url
    if not base:
        return None
    return f"{base.rstrip('/')}/{key}"


def shop_prefix(shop_id: UUID) -> str:
    return R2_KEY_PREFIX.format(shop_id=shop_id)


def _require_r2() -> None:
    if not get_settings().r2_enabled:
        raise AppError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "r2_unavailable",
            "Image uploads are not configured",
        )


def presign(scope: ShopScope, body: PresignIn) -> PresignOut:
    _require_r2()
    if body.content_type not in ALLOWED_IMAGE_TYPES:
        raise unprocessable("invalid_content_type", "Use webp, jpeg, or png")
    scope.require(Product, body.product_id)
    settings = get_settings()
    key = f"{shop_prefix(scope.shop_id)}{uuid.uuid4()}.webp"
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.r2_bucket, "Key": key, "ContentType": body.content_type},
        ExpiresIn=PRESIGN_TTL_SECONDS,
    )
    return PresignOut(upload_url=upload_url, key=key, public_url=public_url_for(key) or "")


def attach_image(scope: ShopScope, product_id: UUID, body: AttachImageIn) -> ImageOut:
    product = scope.require(Product, product_id)
    prefix = shop_prefix(scope.shop_id)
    if not body.key.startswith(prefix):
        raise unprocessable("invalid_key", "Image key does not belong to this shop")
    count = len(
        scope.db.scalars(scope.select(ProductImage).where(ProductImage.product_id == product.id)).all()
    )
    if count >= MAX_IMAGES_PER_PRODUCT:
        raise unprocessable("image_limit", f"A product can have at most {MAX_IMAGES_PER_PRODUCT} images")
    image = ProductImage(
        shop_id=scope.shop_id, product_id=product.id, r2_key=body.key, sort_order=count
    )
    scope.db.add(image)
    commit(scope)
    return ImageOut(id=image.id, public_url=public_url_for(image.r2_key), sort_order=image.sort_order)


def delete_image(scope: ShopScope, image_id: UUID) -> None:
    image = scope.require(ProductImage, image_id)
    scope.db.delete(image)
    commit(scope)
