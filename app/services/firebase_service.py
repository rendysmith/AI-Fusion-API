import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, auth
from app.settings import settings

def initialize_firebase():

    try:

        service_account_content = os.environ.get('FIREBASE_SERVICE_ACCOUNT_CONTENT')

        if service_account_content:

            logging.info("Инициализация Firebase из переменной окружения (Yandex Cloud)...")
            cred_dict = json.loads(service_account_content)
            cred = credentials.Certificate(cred_dict)

        else:

            logging.info(f"Инициализация Firebase из файла: {settings.FIREBASE_SERVICE_ACCOUNT_PATH}...")
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)

        firebase_admin.initialize_app(cred)
        logging.info("Firebase Admin SDK успешно инициализирован.")

    except ValueError as e:

        if "already exists" in str(e):
            logging.warning("Firebase Admin SDK уже был инициализирован.")
        else:
            logging.error(f"Ошибка инициализации Firebase: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Критическая ошибка инициализации Firebase: {e}", exc_info=True)

def verify_firebase_token(token: str) -> dict:

    try:
        return auth.verify_id_token(token)

    except Exception as e:
        raise ValueError(f"Invalid Firebase Token: {e}")


def create_custom_token(uid: str) -> str:
    return auth.create_custom_token(uid).decode('utf-8')