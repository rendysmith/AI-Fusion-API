from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class VisitorTrackRequest(BaseModel):
    visitor_id: UUID
    referrer: Optional[str] = None