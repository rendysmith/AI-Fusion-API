from datetime import datetime
from typing import List, Literal, Optional, Any, Annotated, Union, Dict
from pydantic import BaseModel, Field, model_validator
from .common import BaseModelParams, PromptMixin


GrsaiAspectRatio = Literal[
    "auto",
    "1:1",
    "16:9", "9:16",
    "4:3", "3:4",
    "3:2", "2:3",
    "5:4", "4:5",
    "21:9"
]


class Sora2Params(BaseModelParams, PromptMixin):
    model_name: Literal["sora-2"]


    aspect_ratio: Literal["16:9", "9:16"] = Field("16:9", description="Соотношение сторон")

    duration: Literal[10, 15] = Field(10, description="Длительность видео")

    image_url: str | None = Field(None)


    @model_validator(mode='before')
    @classmethod
    def normalize_orientation(cls, data: Any) -> Any:
        if isinstance(data, dict):

            if 'orientation' in data and 'aspect_ratio' not in data:
                orientation = data.pop('orientation')


                if orientation == 'portrait':
                    data['aspect_ratio'] = '9:16'
                else:
                    data['aspect_ratio'] = '16:9'


            elif 'ratio' in data and 'aspect_ratio' not in data:

                data['aspect_ratio'] = data.pop('ratio').replace('_', ':')

        return data



class Veo3QualityParams(BaseModelParams, PromptMixin):
    model_name: Literal["veo-3-quality"]
    image_url: Optional[str] = Field(None, description='...')
    translate: bool = False
    aspect_ratio: Optional[Literal["16:9", "9:16"]] = Field(None, description="...")

class Veo3FastParams(BaseModelParams, PromptMixin):
    model_name: Literal["veo-3-fast"]
    image_url: Optional[str] = Field(None, description='...')
    translate: bool = False
    aspect_ratio: Optional[Literal["16:9", "9:16"]] = Field(None, description="...")


class NanoBanana(BaseModelParams, PromptMixin):
    model_name: Literal["nano-banana"]
    image_urls: List[str] = Field(default_factory=list, max_length=3)

    aspect_ratio: GrsaiAspectRatio = Field(
        "auto",
        description="Соотношение сторон итогового изображения."
    )


class NanoBananaPro(BaseModelParams, PromptMixin):
    model_name: Literal["nano-banana-pro"]
    image_urls: List[str] = Field(default_factory=list, max_length=3)

    image_size: Literal["1K", "2K", "4K"] = Field(
        "1K",
        description="Разрешение итогового изображения."
    )

    aspect_ratio: GrsaiAspectRatio = Field(
        "auto",
        description="Соотношение сторон итогового изображения."
    )


AnyModelParams = Annotated[
    Union[
        Sora2Params,
        Veo3FastParams,
        Veo3QualityParams,
        NanoBanana,
        NanoBananaPro
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

class GenerationResultModel(BaseModel):
    videoUrl: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    imageUrl: Optional[str] = None

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