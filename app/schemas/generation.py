from datetime import datetime
from typing import List, Literal, Optional, Any, Annotated, Union, Dict
from pydantic import BaseModel, Field
from .common import BaseModelParams, PromptMixin

class Sora2Params(BaseModelParams, PromptMixin):
    model_name: Literal["sora-2"]
    image_url: Optional[str] = Field(None, description="...")
    orientation: Literal["landscape", "portrait"] = Field("landscape", description="...")
    duration: Literal[10, 15] = Field(10, description="...")

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