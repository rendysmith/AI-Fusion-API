from sqlalchemy import Column, String, DateTime, func, BigInteger, Integer, Float, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database.main_models import Base


class GenerationTask(Base):
    __tablename__ = "generation_tasks"


    id = Column(String(36), primary_key=True, index=True)

    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


    user_telegram_id = Column(BigInteger, index=True, nullable=False)
    api_key_id = Column(Integer, index=True, nullable=False)
    model_name = Column(String(100), nullable=False, index=True)

    cost = Column(Float, nullable=False)
    prime_cost = Column(Float, nullable=False)


    params = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)


    error = Column(Text, nullable=True)
    processed_by = Column(String(100), nullable=True)