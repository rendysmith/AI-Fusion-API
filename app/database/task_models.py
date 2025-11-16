from sqlalchemy import Column, String, DateTime, func, Integer, Float, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.base import Base


class GenerationTask(Base):
    __tablename__ = "generation_tasks"


    id = Column(String(36), primary_key=True, index=True)

    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    user = relationship("User", lazy="joined")

    model_slug = Column(String(100), ForeignKey("ai_models.slug"), nullable=False, index=True)
    provider_job_id = Column(String(100), nullable=True, index=True)

    cost = Column(Float, nullable=False)
    prime_cost = Column(Float, nullable=False)


    params = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)


    error = Column(Text, nullable=True)
    processed_by = Column(String(100), nullable=True)