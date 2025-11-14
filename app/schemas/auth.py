from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class TelegramInitRequest(BaseModel):
    link_existing: bool = True

class TelegramInitResponse(BaseModel):
    token: str
    expires_at: datetime
    bot_url: str
    qr_code: str

class TelegramStatusResponse(BaseModel):
    status: str
    expires_at: Optional[datetime] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    linked_at: Optional[datetime] = None

class TelegramWebhookPayload(BaseModel):
    token: str
    telegram_id: int
    username: Optional[str] = None