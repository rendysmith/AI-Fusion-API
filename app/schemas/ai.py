"""AI model Pydantic schemas."""

import json
from datetime import datetime
from typing import Literal, Optional, Any, Dict, List

from pydantic import BaseModel, computed_field, ConfigDict


class ModelPricing(BaseModel):
    """Pricing information for a model."""

    cost: float
    unit: Literal["second", "generation", "image", "video"]
    display_text: str


class AiModelBase(BaseModel):
    """Base AI model fields."""

    name: str
    slug: str
    description: Optional[str] = None
    category: str
    is_available: bool = True
    sort_order: int = 0
    settings: Optional[Dict[str, Any]] = None


class AiModelCreate(AiModelBase):
    """Request to create an AI model."""

    pass


class AiModelUpdate(BaseModel):
    """Request to update an AI model."""

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_available: Optional[bool] = None
    sort_order: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None


class AiModelResponse(AiModelBase):
    """AI model response with computed pricing and ratios."""

    id: int
    created_at: datetime
    updated_at: datetime

    @property
    def _parsed_settings(self) -> dict:
        """Parse settings from JSON string or dict."""
        if isinstance(self.settings, dict):
            return self.settings
        if isinstance(self.settings, str):
            try:
                return json.loads(self.settings)
            except Exception:
                return {}
        return {}

    @computed_field
    def pricing(self) -> ModelPricing:
        """Compute pricing display from settings."""
        settings_data = self._parsed_settings

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
            display_text=f"{base_cost} 💎 {suffix}",
        )

    @computed_field
    def available_ratios(self) -> List[str]:
        """List of available aspect ratios for this model."""
        if self.category not in ["image", "video"]:
            return []

        settings_data = self._parsed_settings

        if "valid_ratios" in settings_data:
            return settings_data["valid_ratios"]

        return ["1:1", "16:9", "9:16"]

    model_config = ConfigDict(from_attributes=True)


class BackendBase(BaseModel):
    """Base backend provider fields."""

    name: Optional[str] = None
    model_name: str
    provider_name: str
    provider: str
    category: Optional[str] = "text"
    sort_priority: int = 1


class BackendCreate(BackendBase):
    """Request to create a backend provider."""

    pass


class BackendUpdate(BaseModel):
    """Request to update a backend provider."""

    name: Optional[str] = None
    model_name: Optional[str] = None
    provider_name: Optional[str] = None
    provider: Optional[str] = None
    sort_priority: Optional[int] = None


class BackendResponse(BackendBase):
    """Backend provider response with timestamps."""

    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
