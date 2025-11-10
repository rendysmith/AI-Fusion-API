import json
import re
from datetime import datetime
from typing import List, Literal, Optional, Any, Annotated, Union, Dict

from pydantic import BaseModel, Field, validator, field_validator, ConfigDict


class BaseModelParams(BaseModel):
    pass


class PromptMixin(BaseModel):
    prompt: str = Field(..., description="Основной промпт для генерации.")



class Sora2Params(BaseModelParams, PromptMixin):
    model_name: Literal["sora-2"]

    image_url: Optional[str] = Field(
        None,
        description="Опциональный URL или Base64 для генерации видео из изображения (Image-to-Video)."
    )

    orientation: Literal["landscape", "portrait"] = Field(
        "landscape",
        description="Ориентация генерируемого видео. По умолчанию 'landscape'."
    )


    duration: Literal[10, 15] = Field(10, description="Длительность видео в секундах. (10 или 15)")


class Veo3QualityParams(BaseModelParams, PromptMixin):
    model_name: Literal["veo-3-quality"]
    image_url: Optional[str] = Field(None, description='URL / Base 64 отправляемой картинки')
    translate: bool = False
    aspect_ratio: Optional[Literal["16:9", "9:16"]] = Field(
        None,
        description="Соотношение сторон для генерируемого видео. Если не указано, будет выбрано значение по умолчанию."
    )

class Veo3FastParams(BaseModelParams, PromptMixin):
    model_name: Literal["veo-3-fast"]
    image_url: Optional[str] = Field(None, description='URL / Base 64 отправляемой картинки')
    translate: bool = False
    aspect_ratio: Optional[Literal["16:9", "9:16"]] = Field(
        None,
        description="Соотношение сторон для генерируемого видео. Если не указано, будет выбрано значение по умолчанию."
    )


AnyModelParams = Annotated[
    Union[
        Sora2Params,
        Veo3FastParams,
        Veo3QualityParams
    ],
    Field(discriminator="model_name")
]

class GenerateRequest(BaseModel):
    params: AnyModelParams

class GenerateAcceptedResponse(BaseModel):
    message: str = "Task accepted for processing"
    task_id: str
    balance: float


TaskStatus = Literal["pending", "processing", "completed", "failed"]


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True



class Balance(BaseModel):
    key_balance: float


class UserStatItem(BaseModel):
    model: str
    count: int


class DailyActivity(BaseModel):
    date: str
    count: int


class UserAnalyticsResponse(BaseModel):
    telegram_id: int
    total_spending: float
    total_tasks: int
    failed_tasks: int
    model_usage: List[UserStatItem]
    daily_activity: List[DailyActivity]


class GenerationResultModel(BaseModel):
    videoUrl: Optional[str] = None
    thumbnailUrl: Optional[str] = None


class GenerationHistoryItem(BaseModel):
    task_id: str
    prompt: Optional[str] = None
    model: str
    status: str
    error: Optional[str] = None
    created_at: datetime
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[GenerationResultModel] = None


class GenerationHistoryResponse(BaseModel):
    generations: List[GenerationHistoryItem]
    total: int
    page: int
    limit: int


class UserBalanceResponse(BaseModel):
    balance: float
    plan: Optional[str] = None
    generations_left: Optional[int] = None


class PlanSchema(BaseModel):
    id: int
    name: str
    slug: str
    generations_per_month: int = Field(alias="generationsPerMonth")

class SubscriptionSchema(BaseModel):
    status: str
    current_period_end: datetime = Field(alias="currentPeriodEnd")

class UserProfileResponse(BaseModel):
    uid: str
    email: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    balance: float
    currency: str = "RUB"
    is_admin: bool = False
    current_plan: Optional[PlanSchema] = None
    subscription: Optional[SubscriptionSchema] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None

    class Config:
        from_attributes = True

class UserProfileUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    display_name: Optional[str] = Field(None, max_length=100)
    photo_url: Optional[str] = Field(None, max_length=255)

    @classmethod
    @field_validator('username')
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v

        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only letters, numbers, and underscores')
        return v



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


class AiModelBase(BaseModel):
    name: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1, pattern=r'^[a-z0-9-]+$')
    description: str
    provider: str
    category: Literal["video", "image", "text", "audio"]
    is_available: bool = True
    is_new: bool = False
    is_best: bool = False
    icon_url: Optional[str] = None
    sort_order: int = 0
    settings: Optional[Dict[str, Any]] = None


class AiModelCreate(AiModelBase):
    is_available: bool | int
    is_new: bool | int
    is_best: bool | int
    settings: Optional[str] = None

    @classmethod
    @field_validator('is_available', 'is_new', 'is_best', mode='before')
    def convert_int_to_bool(cls, v):
        return bool(v)


class AiModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    slug: Optional[str] = Field(None, min_length=1, pattern=r'^[a-z0-9-]+$')
    description: Optional[str] = None
    provider: Optional[str] = None
    category: Optional[Literal["video", "image", "text", "audio"]] = None
    is_available: Optional[bool | int] = None
    is_new: Optional[bool | int] = None
    is_best: Optional[bool | int] = None
    icon_url: Optional[str] = None
    sort_order: Optional[int] = None
    settings: Optional[str | Dict[str, Any]] = None

    @classmethod
    @field_validator('is_available', 'is_new', 'is_best', mode='before')
    def convert_int_to_bool_opt(cls, v):
        if v is not None:
            return bool(v)
        return v


class AiModelResponse(AiModelBase):
    id: int
    settings: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    @field_validator('settings', mode='before')
    def convert_json_to_string(cls, v):
        if isinstance(v, dict):
            return json.dumps(v)
        return v