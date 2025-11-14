from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app import schemas
from app.database.repositories.product_repository import ProductRepository
from app.dependencies import (
    get_product_repository,
    get_current_admin_user
)


router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

@router.get(
    "",
    response_model=List[schemas.ProductResponse],
    summary="Get all active products (credits, subscriptions, etc)"
)
async def get_public_products(
    repo: ProductRepository = Depends(get_product_repository)
):

    return await repo.get_all(only_active=True)



admin_router = APIRouter(
    prefix="/admin/products",
    tags=["Admin: Products"],
    dependencies=[Depends(get_current_admin_user)]
)

@admin_router.get(
    "",
    response_model=List[schemas.ProductResponse],
    summary="[Admin] Get all products"
)
async def get_all_products_admin(
    repo: ProductRepository = Depends(get_product_repository)
):

    return await repo.get_all(only_active=False)

@admin_router.post(
    "",
    response_model=schemas.ProductResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_product(
    payload: schemas.ProductCreate,
    repo: ProductRepository = Depends(get_product_repository)
):

    return await repo.create(payload)

@admin_router.put("/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    repo: ProductRepository = Depends(get_product_repository)
):

    product = await repo.update(product_id, payload)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product

@admin_router.delete("/{product_id}", response_model=schemas.DeleteResponse)
async def delete_product(
    product_id: int,
    repo: ProductRepository = Depends(get_product_repository)
):

    success = await repo.delete(product_id)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    return {"success": True}