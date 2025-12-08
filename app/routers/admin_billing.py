from fastapi import APIRouter, Depends, Query
from app import schemas
from app.dependencies import get_current_admin_user, get_billing_repository
from app.database.repositories.billing_repository import BillingRepository


admin_router = APIRouter(
    prefix="/admin/billing",
    tags=["Admin: Billing"],
    dependencies=[Depends(get_current_admin_user)]
)


@admin_router.get(
    "/payments",
    response_model=schemas.AdminPaymentListResponse,
    summary="[Admin] Get list of all payments"
)
async def get_all_payments(
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=100),
        billing_repo: BillingRepository = Depends(get_billing_repository)
):
    payments, total = await billing_repo.get_all_payments_paginated(page, limit)


    items = []
    for p in payments:
        u_email = p.user.email if p.user else "Deleted User"
        p_name = p.product.name if p.product else "Unknown Product"

        curr = p.product.currency if p.product else "RUB"

        real_amount = float(p.amount)

        items.append(schemas.AdminPaymentItem(
            internal_id=p.internal_id,
            amount=real_amount,

            currency=curr,

            status=p.status,
            provider=p.provider,
            created_at=p.created_at,
            user_email=u_email,
            user_id=p.user_id,
            product_name=p_name
        ))

    return schemas.AdminPaymentListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit
    )