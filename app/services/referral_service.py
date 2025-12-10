from hashids import Hashids
import os

# Лучше брать из переменных окружения
REFERRAL_SALT = os.getenv("REFERRAL_SALT", "super_secret_random_string_salt_for_your_project_2024")
MIN_LENGTH = 8

# Инициализируем один раз на уровне модуля
_hasher = Hashids(salt=REFERRAL_SALT, min_length=MIN_LENGTH)

class HasherRef:
    """
    Убираем async. Hashids работает в CPU, блокировка event loop ничтожна.
    """
    @staticmethod
    def encode(user_id: int) -> str | None:
        if user_id is None:
            return None
        return _hasher.encode(user_id)

    @staticmethod
    def decode(code: str) -> int | None:
        try:
            decoded = _hasher.decode(code)
            if decoded:
                return decoded[0]
            return None
        except Exception:
            return None