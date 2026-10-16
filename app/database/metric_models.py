"""Visitor and analytics tracking models."""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database.base import Base


class Visitor(Base):
    """Tracked website visitor with UTM parameters."""

    __tablename__ = "visitors"

    visitor_id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(Integer, nullable=True)

    first_visit_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    last_visit_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    referrer = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    utm_content = Column(String(100), nullable=True)
    utm_term = Column(String(100), nullable=True)
