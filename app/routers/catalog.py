from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import OwnerUser, Scope
from app.schemas.catalog import (
    AttachImageIn,
    CategoryList,
    ImageOut,
    OwnerProductList,
    OwnerProductOut,
    ProductList,
    ProductPatch,
    ProductWrite,
)
from app.services import catalog as catalog_service
from app.services import uploads as uploads_service

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/categories", response_model=CategoryList, summary="List categories")
def list_categories(scope: Scope) -> CategoryList:
    return CategoryList(items=catalog_service.list_categories(scope))


@router.get("/products", summary="Search products")
def list_products(
    scope: Scope,
    q: str | None = None,
    category_id: UUID | None = None,
    include_inactive: bool = False,
) -> OwnerProductList | ProductList:
    items = catalog_service.list_products(scope, q, category_id, include_inactive)
    if scope.user.role == "owner":
        return OwnerProductList(items=items)  # type: ignore[arg-type]
    return ProductList(items=items)  # type: ignore[arg-type]


@router.post(
    "/products",
    response_model=OwnerProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product (owner)",
)
def create_product(_owner: OwnerUser, scope: Scope, body: ProductWrite) -> OwnerProductOut:
    return catalog_service.create_product(scope, body)


@router.patch("/products/{product_id}", response_model=OwnerProductOut, summary="Update a product (owner)")
def patch_product(_owner: OwnerUser, scope: Scope, product_id: UUID, body: ProductPatch) -> OwnerProductOut:
    return catalog_service.patch_product(scope, product_id, body)


@router.post(
    "/products/{product_id}/images",
    response_model=ImageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an uploaded image to a product (owner)",
)
def attach_image(_owner: OwnerUser, scope: Scope, product_id: UUID, body: AttachImageIn) -> ImageOut:
    return uploads_service.attach_image(scope, product_id, body)


@router.delete(
    "/product-images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a product image (owner)",
)
def delete_image(_owner: OwnerUser, scope: Scope, image_id: UUID) -> None:
    uploads_service.delete_image(scope, image_id)

