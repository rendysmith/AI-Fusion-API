from datetime import datetime
from typing import Optional, Literal, List

from pydantic import BaseModel, Field, ConfigDict, HttpUrl


class ModelT2T(BaseModel):
    prompt: str
    model: str
    session_id: Optional[int] = None
    image_urls: List[HttpUrl] = Field(default_factory=list)


class ChatSessionCreate(BaseModel):
    user_id: int
    model_slug: str = Field(..., max_length=50)
    chat_name: str = "Новый чат"


class ChatMessageCreate(BaseModel):
    session_id: int
    role: Literal['user', 'assistant', 'system']
    message_text: str
    token_count: int = 0

class ChatHistoryRequest(BaseModel):
    session_id: int = Field(..., description="ID существующей сессии чата.")


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    message_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    id: int
    model_slug: str
    chat_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)