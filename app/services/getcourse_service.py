"""GetCourse integration service for payment and deal management."""

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
    """Service for interacting with the GetCourse API."""

    def __init__(
        self,
        api_key: str,
        account_name: str,
        admin_email: str,
        client: aiohttp.ClientSession,
        billing_repo: BillingRepository,
        billing_service: BillingService,
    ):
        self.api_key = api_key
        self.account_name = account_name
        self.admin_email = admin_email
        self.client = client
        self.billing_repo = billing_repo
        self.billing_service = billing_service
        self.deals_url = f"https://{account_name}.getcourse.ru/pl/api/deals"
        self.export_url = (
            f"https://{account_name}.getcourse.ru/pl/api/account/deals"
        )
        self.export_status_url = (
            f"https://{account_name}.getcourse.ru/pl/api/account/exports"
        )

    async def _send_request(
        self, url: str, action: str, params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send a request to the GetCourse API."""
        json_params = json.dumps(params)
        b64_params = base64.b64encode(
            json_params.encode("utf-8"),
        ).decode("utf-8")
        post_data = {"action": action, "key": self.api_key, "params": b64_params}
        try:
            async with self.client.post(url, data=post_data, timeout=15.0) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
                if not data.get("success") or data.get("result", {}).get("error"):
                    error_msg = (
                        data.get("result", {}).get("error_message", "Unknown Error")
                    )
                    logger.error(f"GetCourse API Error: {error_msg}")
                    raise Exception(f"GetCourse API Error: {error_msg}")
                return data.get("result", {})
        except aiohttp.ClientResponseError as e:
            logger.error(f"GetCourse HTTP Error: {e.status} - {e.message}")
            raise Exception(f"GetCourse HTTP Error: {e.request_info.url}")
        except Exception as e:
            logger.error(f"GetCourse General Error: {e}")
            raise e

    async def create_deal(
        self, user: User, product: Product, return_url: str,
    ) -> Dict[str, Any]:
        """Create a deal in GetCourse and return payment link."""
        offer_code = product.external_id_getcourse
        if not offer_code:
            raise ValueError(
                f"Product {product.id} has no 'external_id_getcourse' set",
            )
        params = {
            "user": {
                "email": self.admin_email,
                "first_name": user.display_name
                or user.username
                or f"User {user.id}",
            },
            "system": {
                "refresh_if_exists": 1,
                "return_payment_link": 1,
                "return_deal_number": 1,
                "return_url": return_url,
            },
            "deal": {
                "offer_code": offer_code,
                "deal_cost": str(product.price / 100),
                "deal_status": "new",
            },
        }
        result = await self._send_request(self.deals_url, "add", params)
        if "payment_link" not in result or "deal_number" not in result:
            raise Exception(
                "GetCourse did not return 'payment_link' or 'deal_number'",
            )
        return result

    async def check_pending_deals(self, max_wait_time: int = 60):
        """Check for pending paid deals in GetCourse and process them."""
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
            external_id = deal.get("ID заказа")
            if not external_id or deal.get("Оплачен") != "Да":
                continue

            payment = await self.billing_repo.get_payment_by_external_id(
                external_id, "getcourse",
            )

            if not payment:
                logger.warning(
                    f"CheckDeals: Paid order {external_id} not in 'payments'. "
                    f"Ignoring.",
                )
                continue

            if payment.status == "pending":
                logger.warning(
                    f"CheckDeals: Found 'pending' payment {payment.internal_id} "
                    f"(Deal: {external_id}). Activating...",
                )

                product = await self.billing_repo.get_product(payment.product_id)
                if not product:
                    logger.error(
                        f"CheckDeals: Product {payment.product_id} not found "
                        f"for Payment {payment.internal_id}. Skipping.",
                    )
                    continue

                await self.billing_service.grant_product_rewards(
                    payment.user_id, product,
                )
                await self.billing_repo.complete_payment(payment.internal_id)
                await self.billing_repo.create_invoice(payment)

                processed_count += 1

        logger.info(
            f"CheckDeals: Completed. Processed {processed_count} lost payments.",
        )

    async def _start_deals_export(self, from_time: str) -> Optional[str]:
        """Start a deals export in GetCourse."""
        params = {
            "key": self.api_key,
            "user_email": self.admin_email,
            "payed_at[from]": from_time,
        }
        try:
            async with self.client.get(
                self.export_url, params=params,
            ) as response:
                init_data = await response.json(content_type=None)
            if not init_data.get("success"):
                logger.error(
                    f"CheckDeals (Start): Error {init_data.get('error_message')}",
                )
                return None
            return init_data["info"]["export_id"]
        except Exception as e:
            logger.error(f"CheckDeals (Start) HTTP Error: {e}")
            return None

    async def _get_export_results(
        self, export_id: str, max_wait_time: int,
    ) -> Optional[List[Dict]]:
        """Wait for and retrieve export results from GetCourse."""
        status_url = f"{self.export_status_url}/{export_id}"
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                async with self.client.get(
                    status_url, params={"key": self.api_key},
                ) as response:
                    export_data = await response.json(content_type=None)
                if export_data.get("success") and not export_data.get("error"):
                    fields = export_data["info"]["fields"]
                    items = export_data["info"]["items"]
                    parsed_deals = [
                        {fields[k]: i for k, i in enumerate(item)}
                        for item in items
                    ]
                    if not parsed_deals:
                        logger.info(
                            "CheckDeals (Get): Export successful, no paid orders.",
                        )
                        return None
                    return parsed_deals
                if export_data.get("error") and export_data.get("error_code") == 909:
                    await asyncio.sleep(5)
                    continue
                logger.error(
                    f"CheckDeals (Get): Error {export_data.get('error_message')}",
                )
                return None
            except Exception as e:
                logger.error(f"CheckDeals (Get) HTTP Error: {e}")
                await asyncio.sleep(5)
        logger.warning(
            f"CheckDeals (Get): Timeout waiting for file {export_id}.",
        )
        return None
