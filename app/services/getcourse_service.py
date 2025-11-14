import base64
import json
import time
from datetime import datetime, timedelta

import httpx
import logging
from typing import Dict, Any

from app.database.main_models import User
from app.database.billing_models import Product

from app.database.repositories.billing_repository import BillingRepository
from app.database.repositories.user_repository import UserRepository


logger = logging.getLogger(__name__)


class GetCourseService:
    def __init__(self, api_key: str, account_name: str):
        self.api_key = api_key
        self.account_name = account_name
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

    async def create_deal(self, admin_email, ,user: User, product: Product, return_url: str) -> Dict[str, Any]:
        """
        (POST /billing/checkout)
        Создает "сделку" (заказ) в GetCourse и возвращает ссылку на оплату.
        """


        offer_code = product.external_id_getcourse
        if not offer_code:
            raise ValueError(f"Product {product.id} has no 'external_id_getcourse' set")


        params = {
            "user": {
                "email": admin_email,
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

    async def check_deal_status(self, user_id, admin_email, max_wait_time=60):
        """
        Запрашивает экспорт заказов и ожидает его готовности.

        :param account_name: Имя аккаунта GetCourse
        :param secret_api_key: Секретный API-ключ
        :param admin_email: Email администратора с сайта getcourse (о чего имени формируется счет)
        :param payed_at: Начальная дата оплаты счета
        :param max_wait_time: Максимальное время ожидания в секундах (по умолчанию 60)
        :return: Словарь с данными заказов или None в случае ошибки/таймаута
        """
        now = datetime.now()
        from_time = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        #current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

        url = f'https://{self.account_name}.getcourse.ru/pl/api/account/deals'
        params = {
            'key': self.api_key,
            'user_email': admin_email,
            'payed_at[from]': from_time,
        }

        # 1. Инициируем экспорт
        # response = requests.get(url, params=params)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            init_data = response.json()
            print("Ответ на инициацию экспорта:")
            # print(json.dumps(init_data, indent=2, ensure_ascii=False))

            if not init_data.get('success'):
                print("Ошибка при инициации экспорта:", init_data.get('error_message'))
                return None

            export_id = init_data['info']['export_id']
            print(f"Получен export_id: {export_id}")

        # 2. Ждем готовности файла
        export_url = f"https://{self.account_name}.getcourse.ru/pl/api/account/exports/{export_id}"
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            # response = requests.get(export_url, params={'key': secret_api_key})
            async with httpx.AsyncClient() as client:
                response = await client.get(export_url, params={'key': self.api_key})
                export_data = response.json()
                print("Ответ на проверку готовности:")
                # print(json.dumps(export_data, indent=2, ensure_ascii=False))
                #pprint(export_data)

                if export_data.get('success') and not export_data.get('error'):
                    # Успешно получены данные
                    new_export_data = []
                    fields = export_data['info']['fields']
                    for item in export_data['info']['items']:
                        temp_dict = {}
                        for k, i in enumerate(item):
                            temp_dict[fields[k]] = i
                        new_export_data.append(temp_dict)

                    if len(new_export_data) == 0:
                        return

                    for nwd in new_export_data():
                        if nwd['Оплачен'] == 'Да':
                            external_id = nwd['ID заказа']

                            BR = BillingRepository()
                            payment = await BR.get_payment_by_external_id(external_id)

                            if payment:
                                status = payment.status
                                amount = payment.amount
                                user_id = payment.user_id
                                internal_id = payment.internal_id
                                if status == 'pending': #Если статус ордера = pending
                                    await BR.complete_payment(internal_id) #меняем на completed

                                    #Получаем кол-во кредитов у пользователя
                                    UR = UserRepository()
                                    await UR.refund_balance(user_id, amount)







                                    #


























                    return new_export_data

            if export_data.get('error') and export_data.get('error_code') == 909:  # "Файл еще не создан"
                print("Файл еще не готов, ждем...")
                time.sleep(5)  # Ждем 5 секунд перед повторным запросом
                continue

            # Любая другая ошибка
            print("Ошибка при получении экспорта:", export_data.get('error_message'))
            return None

        print("Таймаут ожидания готовности файла.")
        return None