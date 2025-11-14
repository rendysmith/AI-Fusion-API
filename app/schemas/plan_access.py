from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class PlanModelAccessBase(BaseModel):
    plan_id: int
    model_id: int
    generation_limit: Optional[int] = None

class PlanModelAccessCreate(PlanModelAccessBase):
    pass

class PlanModelAccessResponse(PlanModelAccessBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)