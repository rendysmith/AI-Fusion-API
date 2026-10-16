"""Plan-access linking Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class PlanModelAccessBase(BaseModel):
    """Base plan-model access fields."""

    plan_id: int
    model_id: int
    generation_limit: Optional[int] = None


class PlanModelAccessCreate(PlanModelAccessBase):
    """Request to create a plan-model access entry."""

    pass


class PlanModelAccessResponse(PlanModelAccessBase):
    """Plan-model access response with timestamps."""

    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
