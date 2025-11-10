from sqlalchemy import Column, String, Integer, DateTime, func, Boolean, Float, Text, ForeignKey, UniqueConstraint
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



class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    price = Column(Integer, nullable=False)
    daily_generation_limit = Column(Integer, nullable=False, default=1)
    concurrent_generation_limit = Column(Integer, nullable=False, default=1)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)



class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(String(100), primary_key=True, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    is_manual = Column(Boolean, default=False)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    get_course_deal_id = Column(String(100), nullable=True)
    get_course_deal_number = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PaymentInvoice(Base):
    __tablename__ = "payment_invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(String(100), ForeignKey("user_subscriptions.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    currency = Column(String(10), default="RUB")
    status = Column(String(50), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    failure_reason = Column(Text, nullable=True)



class PlanModelAccess(Base):
    __tablename__ = "plan_model_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=False)
    generation_limit = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint('plan_id', 'model_id', name='uq_plan_model_access'),
    )