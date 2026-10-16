"""Authentication-related Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class TelegramInitRequest(BaseModel):
    """Request to initialize Telegram authentication."""

    link_existing: bool = True


class TelegramInitResponse(BaseModel):
    """Response with Telegram auth token and QR code."""

    token: str
    expires_at: datetime
    bot_url: str
    qr_code: str


class TelegramStatusResponse(BaseModel):
    """Status of a Telegram authentication attempt."""

    status: str
    expires_at: Optional[datetime] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    linked_at: Optional[datetime] = None


class TelegramWebhookPayload(BaseModel):
    """Payload from Telegram webhook for token confirmation."""

    token: str
    telegram_id: int
    username: Optional[str] = None
