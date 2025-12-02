import json
from datetime import datetime
from typing import Literal, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict

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

    @field_validator('settings', mode='before')
    @classmethod
    def convert_json_to_string(cls, v):
        if isinstance(v, dict):
            return json.dumps(v)
        return v

class ModelT2T(BaseModel):
    prompt: str
    provider: str