from fastapi import APIRouter, Depends

from app import schemas
from app.database.repositories.billing_repository import BillingRepository
from app.services.billing_service import BillingService
from app.dependencies import get_billing_repository, get_billing_service


router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)

@router.post("/getcourse")
async def getcourse_webhook(
        payload: schemas.GetCourseWebhook,
        billing_repo: BillingRepository = Depends(get_billing_repository),
        billing_service: BillingService = Depends(get_billing_service)
):

    payment = await billing_repo.get_payment_by_external_id(payload.number)
    if not payment:
        return {"status": "error", "msg": "Payment not found"}

    if payment.status == "completed":
        return {"status": "ok", "msg": "Already processed"}


    if payload.status == "payed":

        product = await billing_repo.get_product(payment.product_id)
        if not product:
             return {"status": "error", "msg": "Product not found for payment"}


        await billing_service.grant_product_rewards(payment.user_id, product)


        await billing_repo.complete_payment(payment.internal_id)
        await billing_repo.create_invoice(payment)

    return {"status": "ok"}