import asyncio
import base64
import json
from pprint import pprint

import httpx
import requests

#from app.settings import settings

# account_name = settings.GETCOURSE_ACCOUNT_NAME
# secret_api_key = settings.GETCOURSE_SECRET_API_KEY

# ПОСЛЕ ТЕСТОВ УДАЛИТЬ! ВЫШЕ РАЗКОММЕНТИТЬ

account_name = "viraltech"
secret_api_key = "2FDXbmarvcnGxDizlTCjUq2k7JjAyhxmz9urwWmSXyv6UZgAxf1ecvRsYdjlJN5jdMgYzCUcKXLCThpDzxWvbVHXiyNbNYjQ2KEzrTtoiIeXO05N6SOl7VJ5U9Zttys6"

class Billing():
    async def create_getcourse_payment(self, user_email, offer_code, deal_cost, product_title):
        """
        Создает заказ в GetCourse и возвращает ссылку на оплату.
        :param account_name: str Название вашего аккаунта в GetCourse (например, 'my-school').
        :param secret_key: str Ваш секретный API-ключ от GetCourse.
        :param user_email: str Email пользователя, для которого создается заказ указан (в личном кабинете во вкладке пользователи)
        :param offer_code: Уникальный код предложения (товара) в GetCourse.
        :param deal_cost: str Стоимость заказа.
        :param product_title: str Название предложения (товара).
        :return:
        {'success': True,
        'action': 'add',
        'result':
        {'success': True,
        'deal_id': 753398816,
        'deal_number': 28,
        'user_id': 477148980,
        'user_status': 'added',
        'error_message': '',
        'error': False,
        'payment_link': 'https://viraltech.getcourse.ru/sales/shop/dealPay/id/753398816/hash/e45cb89d9a4d59471bc2631b92acfe64'}}
        """
        # URL для импорта заказов. Уточните в документации, если он отличается.
        # Обычно это /pl/api/deals или /pl/api/orders

        url = f"https://{account_name}.getcourse.ru/pl/api/deals"

        params = {
            "user": {"email": user_email},
            "system": {'return_payment_link': 1},
            "deal": {
                "offer_code": offer_code,
                "product_title": product_title,
                "deal_cost": deal_cost,
                "deal_status": "new"
            }
        }

        params_json = json.dumps(params).encode('utf-8')
        params_base64 = base64.b64encode(params_json).decode('utf-8')

        payload = {
            'action': 'add',
            'key': secret_api_key,
            'params': params_base64
        }

        headers = {'Accept': 'application/json'}

        try:
            # Используем асинхронный клиент httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=payload, headers=headers)

            response.raise_for_status()
            response_data = response.json()

            # Добавим вывод ответа для отладки
            print("Полный ответ от GetCourse:")
            pprint(response_data)

            if response_data.get("success") and response_data.get("result"):
                payment_link = response_data["result"].get("payment_link")
                if payment_link:
                    return response_data
                else:
                    return f"Ошибка: Ссылка на оплату не найдена в ответе. {response_data.get('error_message')}"
            else:
                return f"Не удалось создать заказ: {response_data.get('error_message')}"

        except httpx.RequestError as e:
            return f"Ошибка при отправке запроса: {e}"
        except json.JSONDecodeError:
            return f"Не удалось декодировать JSON из ответа: {response.text}"

    async def check_deal_status(self, deal_number, user_email):
        """
        Коды статусов заказа (deal_status)
    new — Новый
    payed — Завершен
    cancelled — Отменен
    false — Ложный
    in_work — В работе
    payment_waiting — Ожидаем оплаты
    part_payed — Частично оплачен
    waiting_for_return — Ожидаем возврата
    not_confirmed — Не подтвержден
    pending — Отложен

Коды статусов платежей (payment_status)
    expected — Ожидается
    accepted — Получен
    returned — Возвращен
    tobalance — Пополнение баланса
    frombalance — Списание с баланса
    returned_to_balance — Начисление на депозит
        """
        url = f"https://{account_name}.getcourse.ru/pl/api/deals"

        params = {
            "user": {
                "email": user_email
            },
            "deal": {
                "deal_number": str(deal_number),  # На всякий случай — строка
                "deal_status": "new"
            }
        }
        params_json = json.dumps(params).encode('utf-8')
        params_base64 = base64.b64encode(params_json).decode('utf-8')

        payload = {
            'action': 'add',  # ← Да, action=add!
            'key': secret_api_key,
            'params': params_base64
        }

        headers = {'Accept': 'application/json'}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            print("Проверка статуса заказа:")
            pprint(data)

            if data.get("success") and data.get("result"):
                deal = data["result"]
                status = deal.get("deal_status")
                return {
                    "paid": status == "payed",  # ← Обратите вниманиенение: "payed", не "paid"!
                    "status": status,
                    "deal_number": deal_number,
                    "deal_id": deal.get("deal_id")
                }
            else:
                return {"error": data.get("error_message")}

        except Exception as e:
            return {"error": str(e)}

if "__main__" == __name__:
    bl = Billing()
    user_email = 'ritmorica@gmail.com'


    offer_code = "fr01"
    a = asyncio.run(bl.create_getcourse_payment(user_email,
                                                offer_code,
                                                "100",
                                                'Тестовая покупка'))
    input(a)
#
#     deal_id = "753372837"

    datas = {
        'action': 'add',
        'result': {'deal_id': 753398816,
                   'deal_number': 28,
                   'error': False,
                   'error_message': '',
                   'payment_link': 'https://viraltech.getcourse.ru/sales/shop/dealPay/id/753398816/hash/e45cb89d9a4d59471bc2631b92acfe64',
                   'success': True,
                   'user_id': 477148980,
                   'user_status': 'added'},
        'success': True}

    deal_number = datas['result']['deal_number']
    b = asyncio.run(bl.check_deal_status(deal_number, user_email))
    print(b)

