from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Text
from sqlalchemy.dialects.postgresql import JSONB

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
    __tablename__ = "priority_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=True)
    model_name = Column(String(50), nullable=False)
    provider_name = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    category = Column(String(50), nullable=True)
    sort_priority = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)