import json
from datetime import datetime
from typing import Literal, Optional, Any, Dict

from pydantic import BaseModel, computed_field, ConfigDict


class ModelPricing(BaseModel):
    cost: float
    unit: Literal["second", "generation", "image", "video"]
    display_text: str


class AiModelBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    category: str
    is_available: bool = True
    sort_order: int = 0
    settings: Optional[Dict[str, Any]] = None

class AiModelCreate(AiModelBase):
    pass

class AiModelUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_available: Optional[bool] = None
    sort_order: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None

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

        if manual_unit == "video" or self.category == "video":
            unit = "video"
            suffix = "за видео"
        elif manual_unit == "second":
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


class BackendBase(BaseModel):
    name: Optional[str] = None
    model_name: str
    provider_name: str
    provider: str
    category: Optional[str] = "text"
    sort_priority: int = 1

class BackendCreate(BackendBase):
    pass

class BackendUpdate(BaseModel):
    name: Optional[str] = None
    model_name: Optional[str] = None
    provider_name: Optional[str] = None
    provider: Optional[str] = None
    sort_priority: Optional[int] = None

class BackendResponse(BackendBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)