import json
from datetime import datetime
from typing import Literal, Optional, Any, Dict, List
from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field


class AiModelBase(BaseModel):
    name: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1, pattern=r'^[a-z0-9-./]+$')
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

class ModelPricing(BaseModel):
    cost: float
    unit: Literal["second", "generation", "image", "video"]
    display_text: str


class AiModelResponse(AiModelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    def pricing(self) -> ModelPricing:
        settings_data = {}
        if isinstance(self.settings, str):
            try:
                settings_data = json.loads(self.settings)
            except:
                pass
        elif isinstance(self.settings, dict):
            settings_data = self.settings

        base_cost = float(settings_data.get("cost", 0))

        manual_unit = settings_data.get("unit")

        unit = "generation"
        suffix = "за генерацию"



        if manual_unit == "video":
            unit = "video"
            suffix = "за видео"


        elif manual_unit == "second" or self.slug in ["sora-2", "veo-3-quality", "veo-3-fast"]:
            unit = "second"
            suffix = "за сек."


        elif self.category == "image":
            unit = "image"
            suffix = "за фото"

        return ModelPricing(
            cost=base_cost,
            unit=unit,
            display_text=f"{base_cost} 💎 {suffix}"
        )

    model_config = ConfigDict(from_attributes=True)

class ModelT2T(BaseModel):
    prompt: str
    model: str

# Схема для создания сессии
class ChatSessionCreate(BaseModel):
    user_id: int
    model_slug: str = Field(..., max_length=50)
    chat_name: str = "Новый чат"

# Схема для создания сообщения
class ChatMessageCreate(BaseModel):
    session_id: int
    role: Literal['user', 'assistant', 'system'] # Ограничиваем возможные значения
    message_text: str
    token_count: int = 0

class ChatHistoryRequest(BaseModel):
    session_id: int = Field(..., description="ID существующей сессии чата.")



# Перечисления для строгой типизации параметров Nano Banana
class AspectRatioEnum(str, Enum):
    AUTO = "auto"
    SQUARE = "1:1"
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"
    STANDARD_4_3 = "4:3"
    PORTRAIT_3_4 = "3:4"
    PHOTO_3_2 = "3:2"
    PORTRAIT_2_3 = "2:3"
    LANDSCAPE_5_4 = "5:4"
    PORTRAIT_4_5 = "4:5"
    WIDE_21_9 = "21:9"

class ImageSizeEnum(str, Enum):
    K1 = "1K"
    K2 = "2K"
    K4 = "4K"

class NanoBananaModelEnum(str, Enum):
    FAST = "nano-banana-fast"
    NORMAL = "nano-banana"
    PRO = "nano-banana-pro"
    PRO_VT = "nano-banana-pro-vt"

# --- Request Schemas ---

class GenerateRequest(BaseModel):
    model: NanoBananaModelEnum = Field(..., description="Модель для генерации", example="nano-banana")
    prompt: str = Field(..., description="Текстовое описание изображения", example="A beautiful girl with long hair")
    aspectRatio: Optional[AspectRatioEnum] = Field("auto", description="Соотношение сторон")
    imageSize: Optional[ImageSizeEnum] = Field("1K", description="Разрешение (только для Pro моделей)")
    urls: Optional[List[str]] = Field(None, description="Ссылки на референсные изображения")
    webHook: Optional[str] = Field("-1", description="URL для коллбека. Если '-1', возвращает ID сразу для пулинга.")
    shutProgress: Optional[bool] = Field(False, description="Отключить уведомления о прогрессе")

class GetResultRequest(BaseModel):
    id: str = Field(..., description="ID задачи генерации")

# --- Response Schemas ---

class GenerationResultItem(BaseModel):
    url: str
    content: Optional[str] = None

class GenerationResponse(BaseModel):
    id: str
    results: Optional[List[GenerationResultItem]] = None
    progress: Optional[int] = 0
    status: str
    failure_reason: Optional[str] = None
    error: Optional[str] = None

class PollingResponseWrapper(BaseModel):
    code: int
    msg: str
    data: GenerationResponse
