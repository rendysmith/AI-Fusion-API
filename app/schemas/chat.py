"""Chat and text-to-text Pydantic schemas."""

from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field, ConfigDict, HttpUrl


class ModelT2T(BaseModel):
    """Text-to-text model request."""

    prompt: str
    model: str
    session_id: Optional[int] = None
    image_urls: List[HttpUrl] = Field(default_factory=list)


class ChatSessionCreate(BaseModel):
    """Request to create a chat session."""

    user_id: int
    model_slug: str = Field(..., max_length=50)
    chat_name: str = "Новый чат"


class ChatMessageCreate(BaseModel):
    """Request to create a chat message."""

    session_id: int
    role: Literal["user", "assistant", "system"]
    message_text: str
    token_count: int = 0


class ChatHistoryRequest(BaseModel):
    """Request to retrieve chat history."""

    session_id: int = Field(..., description="ID существующей сессии чата.")


class ChatMessageResponse(BaseModel):
    """Chat message response."""

    id: int
    role: str
    message_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    """Chat session response."""

    id: int
    model_slug: str
    chat_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
