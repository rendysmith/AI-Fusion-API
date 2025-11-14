import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app import schemas
from app.database.main_models import User
from app.database.repositories.billing_repository import BillingRepository
from app.database.repositories.subscription_repository import SubscriptionRepository
from app.dependencies import get_current_user, get_billing_repository, get_subscription_repository, \
    get_getcourse_service
from app.services.getcourse_service import GetCourseService
from app.settings import settings

router = APIRouter(
    prefix="/billing", 
    tags=["Billing"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/checkout", response_model=schemas.CheckoutResponse)
async def checkout(
    payload: schemas.CheckoutRequest,
    user: User = Depends(get_current_user),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    gc_service: GetCourseService = Depends(get_getcourse_service)
):
    product = await billing_repo.get_product(payload.product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")


    try:

        return_url = f"https://{settings.FRONTEND_DOMAIN}/payment/success"

        gc_result = await gc_service.create_deal(
            user=user,
            product=product,
            return_url=return_url
        )

        payment_link = gc_result.get("payment_link")
        deal_id = gc_result.get("deal_id")

        if not payment_link or not deal_id:
            raise Exception("GetCourse response invalid")

    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Payment provider error: {e}")


    payment = await billing_repo.create_payment(
        user_id=user.id,
        product_id=product.id,
        amount=product.price,
        provider="getcourse",
        external_id=deal_id
    )

    return {
        "success": True,
        "payment_link": payment_link,
        "payment_id": payment.internal_id,
        "product": product
    }


@router.get("/payment-status", response_model=schemas.PaymentStatusResponse)
async def get_payment_status(
        payment_id: str = Query(...),
        user: User = Depends(get_current_user),
        billing_repo: BillingRepository = Depends(get_billing_repository),
        sub_repo: SubscriptionRepository = Depends(get_subscription_repository)
):
    payment = await billing_repo.get_payment_by_internal_id(payment_id)
    if not payment or payment.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    sub_dto = None
    if payment.status == "completed" and payment.subscription_id:


        subscription_db = await sub_repo.get_active_subscription_with_plan(user.id)
        if subscription_db:
            sub_dto = schemas.SubscriptionDetailResponse.model_validate(subscription_db)

    return schemas.PaymentStatusResponse(
        payment_id=payment.internal_id,
        status=payment.status,
        provider=payment.provider,
        subscription=sub_dto
    )



@router.post("/cancel", response_model=schemas.CanceledSubscriptionResponse)
async def cancel_subscription(
        user: User = Depends(get_current_user),
        sub_repo: SubscriptionRepository = Depends(get_subscription_repository)
):
    canceled_sub_db = await sub_repo.cancel_subscription(user.id)

    if not canceled_sub_db:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active subscription found")

    canceled_dto = schemas.SubscriptionDetailResponse.model_validate(canceled_sub_db)

    return schemas.CanceledSubscriptionResponse(
        success=True,
        message="Subscription cancelled successfully.",
        subscription=canceled_dto
    )



@router.get("/invoices", response_model=List[schemas.InvoiceResponse])
async def get_invoices(
        limit: int = Query(10, ge=1, le=100),
        offset: int = Query(0, ge=0),
        user: User = Depends(get_current_user),
        billing_repo: BillingRepository = Depends(get_billing_repository)
):

    invoices = await billing_repo.get_user_invoices(user.id, limit, offset)
    return invoices