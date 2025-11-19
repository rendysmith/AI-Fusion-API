import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import schemas
from app.database.repositories.billing_repository import BillingRepository
from app.services.billing_service import BillingService
from app.dependencies import get_billing_repository, get_billing_service
from app.settings import settings

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)


@router.post("/getcourse")
@router.get("/getcourse")
async def getcourse_webhook(

        deal_number: str = Query(..., description="Номер заказа в GetCourse ({object.number})"),
        deal_status: str = Query(..., description="Статус заказа ({object.status})"),
        email: str = Query(None, description="Email юзера ({object.user.email})"),
        secret: str = Query(None),
        # ---------------------------------------

        billing_repo: BillingRepository = Depends(get_billing_repository),
        billing_service: BillingService = Depends(get_billing_service),
):
    """
    Принимает webhook от GetCourse.
    Данные приходят в query params, даже при POST.
    """

    logging.info(f'Deal Number: {deal_number}\nDeal Status: {deal_status}\nEmail: {email}\nSecret: {secret}')


    if not secret or secret != settings.GETCOURSE_WEBHOOK_SECRET:
        logging.warning(f"GC Webhook: Invalid secret '{secret}' for deal {deal_number}")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid secret")


    payment = await billing_repo.get_payment_by_external_id(deal_number, "getcourse")

    logging.info(payment)

    if not payment:
        logging.warning(f"GC Webhook: Payment not found for deal {deal_number}. Ignoring.")
        return {"success": True}


    if payment.status == "completed":
        logging.info(f"GC Webhook: Payment {payment.internal_id} already processed.")
        return {"success": True}



    is_really_paid = False

    if deal_status == "Завершен":

        logging.info(f'Deal Status: {deal_status}')

        is_really_paid = True

    if is_really_paid:
        product = await billing_repo.get_product(payment.product_id)
        if not product:
            logging.error(f"GC Webhook: Product {payment.product_id} not found!")
            return {"success": False, "msg": "Product error"}

        await billing_service.grant_product_rewards(payment.user_id, product)


        await billing_repo.complete_payment(payment.internal_id)
        await billing_repo.create_invoice(payment)

        logging.info(f"GC Webhook: Success! Payment {payment.internal_id} completed.")

    elif deal_status in ["Отменен", "Ложный"]:
        logging.info(f"GC Webhook: Deal {deal_number} cancelled.")

    return {"success": True}