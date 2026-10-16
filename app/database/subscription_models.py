"""Subscription plan and user subscription models."""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func, Float,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class SubscriptionPlan(Base):
    """Available subscription plan definition."""

    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    price = Column(Integer, nullable=False)
    credits_granted = Column(Integer, nullable=False, default=0)
    concurrent_generation_limit = Column(Integer, nullable=False, default=1)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)

    has_unlimited = Column(Boolean, default=False, nullable=False)

    unlimited_delay_factor = Column(Float, default=1.0, nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserSubscription(Base):
    """Active user subscription linking a user to a plan."""

    __tablename__ = "user_subscriptions"

    id = Column(String(100), primary_key=True, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(
        Integer, ForeignKey("subscription_plans.id"), nullable=False, index=True,
    )
    status = Column(String(50), nullable=False, index=True)
    is_manual = Column(Boolean, default=False)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    get_course_deal_id = Column(String(100), nullable=True)
    get_course_deal_number = Column(String(100), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan = relationship("SubscriptionPlan", lazy="joined")
