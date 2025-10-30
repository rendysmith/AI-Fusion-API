from datetime import datetime
from typing import List, Literal, Optional, Any, Annotated, Union

from pydantic import BaseModel, Field

class BaseModelParams(BaseModel):
    pass


class PromptMixin(BaseModel):
    prompt: str = Field(..., description="Основной промпт для генерации.")



class SoraParams(BaseModelParams, PromptMixin):
    model_name: Literal["sora"]

    image_url: Optional[str] = Field(
        None,
        description="Опциональный URL или Base64 для генерации видео из изображения (Image-to-Video)."
    )

    orientation: Literal["landscape", "portrait"] = Field(
        "landscape",
        description="Ориентация генерируемого видео. По умолчанию 'landscape'."
    )


    duration: Literal[10, 15] = Field(10, description="Длительность видео в секундах. (10 или 15)")





AnyModelParams = Annotated[
    Union[
        SoraParams
    ],
    Field(discriminator="model_name")
]

class GenerateRequest(BaseModel):
    params: AnyModelParams

class GenerateAcceptedResponse(BaseModel):
    message: str = "Task accepted for processing"
    task_id: str


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