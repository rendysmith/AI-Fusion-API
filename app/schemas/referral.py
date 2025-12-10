from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from decimal import Decimal


# То, что приходит от фронтенда
class UserRegisterRequest(BaseModel):
    firebase_uid: str = Field(..., description="UID из Firebase")
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

    # Реферальный код (может быть null, если юзер пришел сам)
    referral_code: Optional[str] = None


# То, что отдаем обратно
class UserResponse(BaseModel):
    id: int
    email: Optional[str]
    username: Optional[str]
    balance: Decimal
    referral_code: Optional[str]  # Вычисляемое поле

    class Config:
        from_attributes = True  # В старых версиях Pydantic это orm_mode = True