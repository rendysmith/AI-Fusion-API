from typing import Optional, List

from pydantic import BaseModel


class ServiceStatusItem(BaseModel):
    model_slug: str
    model_name: str
    provider: str
    is_circuit_open: bool
    last_error: Optional[str] = None

class SystemHealthResponse(BaseModel):
    services: List[ServiceStatusItem]