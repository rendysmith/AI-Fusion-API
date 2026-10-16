"""System health monitoring Pydantic schemas."""

from typing import Optional, List
from pydantic import BaseModel


class ServiceStatusItem(BaseModel):
    """Status of a single AI model service."""

    model_slug: str
    model_name: str
    provider: str
    is_circuit_open: bool
    last_error: Optional[str] = None


class SystemHealthResponse(BaseModel):
    """Overall system health status."""

    services: List[ServiceStatusItem]
