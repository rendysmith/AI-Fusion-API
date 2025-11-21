from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database.base import Base


class Visitor(Base):
    __tablename__ = "visitors"

    visitor_id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(Integer, nullable=True)

    first_visit_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_visit_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    referrer = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)