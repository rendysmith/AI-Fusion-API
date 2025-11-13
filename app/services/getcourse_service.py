import base64
import json
import httpx
import logging
from typing import Dict, Any

from app.database.main_models import User
from app.database.billing_models import Product
from app.settings import settings

logger = logging.getLogger(__name__)


class GetCourseService:
    def __init__(self, api_key: str, account_name: str):
        self.api_key = api_key
        self.deals_url = f"https://{account_name}.getcourse.ru/pl/api/deals"

    async def _send_request(self, url: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Универсальный "отправщик", который кодирует payload.
        """

        json_params = json.dumps(params)
        b64_params = base64.b64encode(json_params.encode('utf-8')).decode('utf-8')


        post_data = {
            "action": action,
            "key": self.api_key,
            "params": b64_params
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=post_data, timeout=15.0)
                response.raise_for_status()

                data = response.json()


                if not data.get("success") or data.get("result", {}).get("error"):
                    error_msg = data.get("result", {}).get("error_message", "Unknown GetCourse Error")
                    logger.error(f"GetCourse API Error: {error_msg}")
                    raise Exception(f"GetCourse API Error: {error_msg}")

                return data.get("result", {})

            except httpx.HTTPStatusError as e:
                logger.error(f"GetCourse HTTP Error: {e.response.status_code} - {e.response.text}")
                raise Exception(f"GetCourse HTTP Error: {e.request.url}")
            except Exception as e:
                logger.error(f"GetCourse General Error: {e}")
                raise e

    async def create_deal(self, user: User, product: Product, return_url: str) -> Dict[str, Any]:
        """
        (POST /billing/checkout)
        Создает "сделку" (заказ) в GetCourse и возвращает ссылку на оплату.
        """


        offer_code = product.external_id_getcourse
        if not offer_code:
            raise ValueError(f"Product {product.id} has no 'external_id_getcourse' set")


        params = {
            "user": {
                "email": user.email,
                "first_name": user.display_name or user.username or f"User {user.id}"
            },
            "system": {
                "refresh_if_exists": 1,
                "return_payment_link": 1,
                "return_deal_number": 1,
                "return_url": return_url
            },
            "deal": {
                "offer_code": offer_code,

                "deal_status": "new"
            }
        }


        result = await self._send_request(self.deals_url, "add", params)


        if "payment_link" not in result or "deal_number" not in result:
            raise Exception("GetCourse did not return 'payment_link' or 'deal_number'")

        return result