from datetime import datetime
from typing import List, Literal, Optional, Any, Annotated, Union, Dict

from pydantic import BaseModel, Field

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