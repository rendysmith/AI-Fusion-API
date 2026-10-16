"""Firebase Admin SDK initialization and token verification."""

import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, auth
from app.settings import settings


def initialize_firebase():
    """Initialize the Firebase Admin SDK from env var or file."""
    try:
        service_account_content = os.environ.get("FIREBASE_SERVICE_ACCOUNT_CONTENT")

        if service_account_content:
            logging.info("Initializing Firebase from environment variable (Yandex Cloud)...")
            cred_dict = json.loads(service_account_content)
            cred = credentials.Certificate(cred_dict)
        else:
            logging.info(
                f"Initializing Firebase from file: {settings.FIREBASE_SERVICE_ACCOUNT_PATH}...",
            )
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)

        firebase_admin.initialize_app(cred)
        logging.info("Firebase Admin SDK initialized successfully.")

    except ValueError as e:
        if "already exists" in str(e):
            logging.warning("Firebase Admin SDK was already initialized.")
        else:
            logging.error(f"Firebase initialization error: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Firebase critical error: {e}", exc_info=True)


def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return its decoded claims."""
    try:
        return auth.verify_id_token(token)
    except Exception as e:
        raise ValueError(f"Invalid Firebase Token: {e}")


def create_custom_token(uid: str) -> str:
    """Create a Firebase custom token for a user."""
    return auth.create_custom_token(uid).decode("utf-8")
