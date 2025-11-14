import asyncio
import base64
import json
import time
from datetime import datetime, timedelta

import aiohttp
import logging
from typing import Dict, Any, List, Optional

from app.database.main_models import User
from app.database.billing_models import Product

from app.database.repositories.billing_repository import BillingRepository
from app.services.billing_service import BillingService


logger = logging.getLogger(__name__)


class GetCourseService:
    def __init__(self, api_key: str, account_name: str, admin_email: str, client: aiohttp.ClientSession):
        self.api_key = api_key
        self.account_name = account_name
        self.admin_email = admin_email
        self.client = client
        self.deals_url = f"https://{account_name}.getcourse.ru/pl/api/deals"
        self.export_url = f"https://{account_name}.getcourse.ru/pl/api/account/deals"
        self.export_status_url = f"https://{account_name}.getcourse.ru/pl/api/account/exports"

    async def _send_request(self, url: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:

        json_params = json.dumps(params)
        b64_params = base64.b64encode(json_params.encode('utf-8')).decode('utf-8')
        post_data = {"action": action, "key": self.api_key, "params": b64_params}
        try:
            async with self.client.post(url, data=post_data, timeout=15.0) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
                if not data.get("success") or data.get("result", {}).get("error"):
                    error_msg = data.get("result", {}).get("error_message", "Unknown GetCourse Error")
                    logger.error(f"GetCourse API Error: {error_msg}")
                    raise Exception(f"GetCourse API Error: {error_msg}")
                return data.get("result", {})
        except aiohttp.ClientResponseError as e:
            logger.error(f"GetCourse HTTP Error: {e.status} - {e.message}")
            raise Exception(f"GetCourse HTTP Error: {e.request_info.url}")
        except Exception as e:
            logger.error(f"GetCourse General Error: {e}")
            raise e

    async def create_deal(self, user: User, product: Product, return_url: str) -> Dict[str, Any]:

        offer_code = product.external_id_getcourse
        if not offer_code:
            raise ValueError(f"Product {product.id} has no 'external_id_getcourse' set")
        params = {
            "user": {"email": self.admin_email, "first_name": user.display_name or user.username or f"User {user.id}"},
            "system": {"refresh_if_exists": 1, "return_payment_link": 1, "return_deal_number": 1,
                       "return_url": return_url},
            "deal": {"offer_code": offer_code, "deal_status": "new"}
        }
        result = await self._send_request(self.deals_url, "add", params)
        if "payment_link" not in result or "deal_number" not in result:
            raise Exception("GetCourse did not return 'payment_link' or 'deal_number'")
        return result

    async def check_pending_deals(
            self,
            billing_repo: BillingRepository,
            billing_service: BillingService,
            max_wait_time: int = 60
    ):
        """
        (CRON / 5 мин)
        "Страховка" от потерянных вебхуков.
        """
        now = datetime.now()
        from_time = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

        export_id = await self._start_deals_export(from_time)
        if not export_id:
            return

        paid_deals = await self._get_export_results(export_id, max_wait_time)
        if not paid_deals:
            return

        processed_count = 0
        for deal in paid_deals:
            external_id = deal.get('ID заказа')
            if not external_id or deal.get('Оплачен') != 'Да':
                continue

            payment = await billing_repo.get_payment_by_external_id(external_id)

            if not payment:
                logger.warning(
                    f"CheckDeals: Найден оплаченный заказ {external_id}, но его нет в 'payments'. Игнорируем.")
                continue

            if payment.status == 'pending':
                logger.warning(
                    f"CheckDeals: Найден 'pending' платеж {payment.internal_id} (Deal: {external_id}). Активируем...")

                product = await billing_repo.get_product(payment.product_id)
                if not product:
                    logger.error(
                        f"CheckDeals: Не найден Product {payment.product_id} для Payment {payment.internal_id}. Пропускаем.")
                    continue


                await billing_service.grant_product_rewards(payment.user_id, product)


                await billing_repo.complete_payment(payment.internal_id)
                await billing_repo.create_invoice(payment)

                processed_count += 1

        logger.info(f"CheckDeals: Завершено. Обработано {processed_count} 'потерянных' платежей.")
        return

    async def _start_deals_export(self, from_time: str) -> Optional[str]:

        params = {'key': self.api_key, 'user_email': self.admin_email, 'payed_at[from]': from_time}
        try:
            async with self.client.get(self.export_url, params=params) as response:
                init_data = await response.json(content_type=None)
            if not init_data.get('success'):
                logger.error(f"CheckDeals (Start): Ошибка {init_data.get('error_message')}")
                return None
            return init_data['info']['export_id']
        except Exception as e:
            logger.error(f"CheckDeals (Start) HTTP Error: {e}")
            return None

    async def _get_export_results(self, export_id: str, max_wait_time: int) -> Optional[List[Dict]]:

        status_url = f"{self.export_status_url}/{export_id}"
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                async with self.client.get(status_url, params={'key': self.api_key}) as response:
                    export_data = await response.json(content_type=None)
                if export_data.get('success') and not export_data.get('error'):
                    fields = export_data['info']['fields']
                    items = export_data['info']['items']
                    parsed_deals = [{fields[k]: i for k, i in enumerate(item)} for item in items]
                    if not parsed_deals:
                        logger.info("CheckDeals (Get): Экспорт успешен, но нет оплаченных заказов.")
                        return None
                    return parsed_deals
                if export_data.get('error') and export_data.get('error_code') == 909:
                    await asyncio.sleep(5)
                    continue
                logger.error(f"CheckDeals (Get): Ошибка {export_data.get('error_message')}")
                return None
            except Exception as e:
                logger.error(f"CheckDeals (Get) HTTP Error: {e}")
                await asyncio.sleep(5)
        logger.warning(f"CheckDeals (Get): Таймаут ожидания файла {export_id}.")
        return None