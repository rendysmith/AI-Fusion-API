import logging

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

    payment = await billing_repo.get_payment_by_external_id(
        external_id=payload.deal_number
    )
    if not payment:

        logging.warning(f"GetCourse webhook: Payment not found for deal_number {payload.deal_number}")
        return {"success": True}

    if payment.status == "completed":
        logging.info(f"GetCourse webhook: Payment {payment.internal_id} already processed. Ignoring.")
        return {"success": True}


    if payload.deal_status == "payed":

        product = await billing_repo.get_product(payment.product_id)
        if not product:
            logging.error(
                f"GetCourse webhook: Product {payment.product_id} not found for payment {payment.internal_id}")
            return {"success": False, "msg": "Product not found"}


        await billing_service.grant_product_rewards(payment.user_id, product)


        await billing_repo.complete_payment(payment.internal_id)
        await billing_repo.create_invoice(payment)

        logging.info(f"Payment {payment.internal_id} (Deal: {payload.deal_number}) completed successfully.")

    elif payload.deal_status in ["cancelled", "false"]:

        pass

    return {"success": True}