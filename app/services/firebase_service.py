import logging

import firebase_admin
from firebase_admin import credentials, auth
from app.settings import settings

def initialize_firebase():

    try:
        firebase_admin.get_app()

    except ValueError:
        cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
        logging.info("Firebase Admin SDK успешно инициализирован.")

def verify_firebase_token(token: str) -> dict:

    try:
        return auth.verify_id_token(token)

    except Exception as e:
        raise ValueError(f"Invalid Firebase Token: {e}")


def create_custom_token(uid: str) -> str:
    return auth.create_custom_token(uid).decode('utf-8')