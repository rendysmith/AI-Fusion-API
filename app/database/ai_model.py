from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.base import Base


class AiModel(Base):
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    provider = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    is_available = Column(Boolean, default=True, nullable=False)
    is_new = Column(Boolean, default=False, nullable=False)
    is_best = Column(Boolean, default=False, nullable=False)
    icon_url = Column(String(255), nullable=True)
    sort_order = Column(Integer, default=0)
    settings = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PriorityModel(Base):
    __tablename__ = "ai_model_backends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=True)
    model_name = Column(String(50), nullable=False)
    provider_name = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    category = Column(String(50), nullable=True)
    sort_priority = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ChatSession(Base):
    __abstract__ = True
    __tablename__ = "chat_sessions"


    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    model_slug = Column(String(50), nullable=False)
    chat_name = Column(String(255), nullable=False, default='Новый чат')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Связь с сообщениями
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __abstract__ = True
    __tablename__ = "chat_messages"


    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    message_text = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связь с сессией
    session = relationship("ChatSession", back_populates="messages")