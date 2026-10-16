"""Chat session and message database models."""

from sqlalchemy import Integer, Column, Text, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.database.base import Base


class ChatSession(Base):
    """A chat session belonging to a user for a specific model."""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    model_slug = Column(String(50), nullable=False)
    chat_name = Column(String(255), nullable=False, default="Новый чат")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now(),
    )

    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan",
    )


class ChatMessage(Base):
    """A single message within a chat session."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False,
    )
    role = Column(String(20), nullable=False)
    message_text = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
