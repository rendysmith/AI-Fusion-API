from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class VideoTemplateBase(BaseModel):
    video_url: str
    thumbnail_url: str
    title: str
    views_count: Optional[str] = None
    prompt: str
    platform_icon: Optional[str] = None
    row_number: Optional[int] = 1
    position: Optional[int] = 1

class VideoTemplateCreate(VideoTemplateBase):
    pass

class VideoTemplateUpdate(BaseModel):
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    views_count: Optional[str] = None
    prompt: Optional[str] = None
    platform_icon: Optional[str] = None
    row_number: Optional[int] = None
    position: Optional[int] = None

class VideoTemplateResponse(VideoTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)