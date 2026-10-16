"""Billing and payment database models."""

from sqlalchemy import (
    Column, String, Integer, DateTime, func, Boolean, Text, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.base import Base


class PlanModelAccess(Base):
    """Defines which AI models are accessible per subscription plan."""

    __tablename__ = "plan_model_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=False)
    generation_limit = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    __table_args__ = (
        UniqueConstraint("plan_id", "model_id", name="uq_plan_model_access"),
    )


class Product(Base):
    """Universal product with reward configuration stored in JSONB."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    price = Column(Integer, nullable=False)
    currency = Column(String(10), default="RUB")

    display_type = Column(String(50), nullable=False)

    rewards = Column(JSONB, nullable=False, server_default="{}")

    external_id_getcourse = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Payment(Base):
    """Payment transaction record linking internal and external payment IDs."""

    __tablename__ = "payments"

    internal_id = Column(String(36), primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    provider = Column(String(50), nullable=False)
    external_payment_id = Column(String(100), nullable=True, index=True)

    amount = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)

    subscription_id = Column(
        String(100), ForeignKey("user_subscriptions.id"), nullable=True,
    )

    provider_metadata = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", lazy="selectin")
    product = relationship("Product", lazy="selectin")


class PaymentInvoice(Base):
    """Invoice record for successfully completed payments."""

    __tablename__ = "payment_invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    payment_id = Column(
        String(36), ForeignKey("payments.internal_id"), nullable=False,
    )

    amount = Column(Integer, nullable=False)
    currency = Column(String(10), default="RUB")
    status = Column(String(50), nullable=False)

    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
