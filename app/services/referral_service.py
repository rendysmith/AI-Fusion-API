"""Referral code encoding/decoding service using Hashids."""

from hashids import Hashids
import os

REFERRAL_SALT = os.getenv(
    "REFERRAL_SALT",
    "super_secret_random_string_salt_for_your_project_2024",
)
MIN_LENGTH = 8

_hasher = Hashids(salt=REFERRAL_SALT, min_length=MIN_LENGTH)


class HasherRef:
    """Hashids-based referral code encoder/decoder.

    This is synchronous — Hashids CPU time is negligible for the event loop.
    """

    @staticmethod
    def encode(user_id: int) -> str | None:
        """Encode a user ID into a referral code string."""
        if user_id is None:
            return None
        return _hasher.encode(user_id)

    @staticmethod
    def decode(code: str) -> int | None:
        """Decode a referral code string back to a user ID."""
        try:
            decoded = _hasher.decode(code)
            if decoded:
                return decoded[0]
            return None
        except Exception:
            return None
