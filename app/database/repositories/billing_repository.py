"""Billing data access repository."""

import uuid
from datetime import datetime, timezone, date

from sqlalchemy import select, update, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional, Any, Sequence, Tuple

from sqlalchemy.orm import selectinload

from app.database.billing_models import Product, Payment, PaymentInvoice
from app.database.main_models import User


class BillingRepository:
    """Repository for billing-related operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_product(self, product_id: int) -> Optional[Product]:
        """Get a product by its ID."""
        async with self.session_factory() as session:
            return await session.get(Product, product_id)

    async def get_all_products(self) -> Sequence[Product]:
        """Get all active products ordered by sort_order."""
        async with self.session_factory() as session:
            stmt = (
                select(Product)
                .where(Product.is_active == True)
                .order_by(Product.sort_order)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create_payment(
        self, user_id: int, product_id: int, amount: int,
        provider: str, external_id: Any,
    ) -> Payment:
        """Create a new payment record."""
        async with self.session_factory() as session:
            external_id_str = str(external_id) if external_id is not None else None

            payment = Payment(
                internal_id=f"pay_{uuid.uuid4().hex}",
                user_id=user_id,
                product_id=product_id,
                amount=amount,
                provider=provider,
                external_payment_id=external_id_str,
                status="pending",
            )
            session.add(payment)
            await session.commit()
            await session.refresh(payment)
            return payment

    async def get_payment_by_external_id(
        self, external_id: Any, provider: str,
    ) -> Optional[Payment]:
        """Get a payment by its external ID and provider."""
        external_id_str = str(external_id) if external_id is not None else None

        async with self.session_factory() as session:
            stmt = select(Payment).where(
                Payment.external_payment_id == external_id_str,
                Payment.provider == provider,
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def complete_payment(self, internal_id: str):
        """Mark a payment as completed."""
        async with self.session_factory() as session:
            await session.execute(
                update(Payment)
                .where(Payment.internal_id == internal_id)
                .values(status="completed"),
            )
            await session.commit()

    async def create_invoice(self, payment: Payment):
        """Create an invoice for a completed payment."""
        async with self.session_factory() as session:
            invoice = PaymentInvoice(
                user_id=payment.user_id,
                payment_id=payment.internal_id,
                amount=payment.amount,
                status="paid",
                paid_at=func.now(),
            )
            session.add(invoice)
            await session.commit()

    async def get_user_invoices(
        self, user_id: int, limit: int, offset: int,
    ) -> Sequence[PaymentInvoice]:
        """Get paginated invoices for a user."""
        async with self.session_factory() as session:
            stmt = (
                select(PaymentInvoice)
                .where(PaymentInvoice.user_id == user_id)
                .order_by(PaymentInvoice.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_payment_by_internal_id(
        self, internal_id: str,
    ) -> Optional[Payment]:
        """Get a payment by its internal ID."""
        async with self.session_factory() as session:
            return await session.get(Payment, internal_id)

    async def get_all_payments_paginated(
        self,
        page: int,
        limit: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[str] = None,
        provider: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> Tuple[List[Payment], int]:
        """Get paginated payments with optional filters."""
        offset = (page - 1) * limit

        async with self.session_factory() as session:
            stmt = (
                select(Payment)
                .options(selectinload(Payment.user), selectinload(Payment.product))
                .order_by(desc(Payment.created_at))
            )

            if date_from and date_to:
                start_dt = datetime.combine(
                    date_from, datetime.min.time(), tzinfo=timezone.utc,
                )
                end_dt = datetime.combine(
                    date_to, datetime.max.time(), tzinfo=timezone.utc,
                )
                stmt = stmt.where(Payment.created_at.between(start_dt, end_dt))

            if status:
                stmt = stmt.where(Payment.status == status)
            if provider:
                stmt = stmt.where(Payment.provider == provider)

            if search_query:
                stmt = stmt.join(Payment.user)

                search_pattern = f"%{search_query}%"
                stmt = stmt.where(
                    or_(
                        User.email.ilike(search_pattern),
                        (User.id == int(search_query))
                        if search_query.isdigit()
                        else False,
                    )
                )

            count_query = select(func.count()).select_from(stmt.subquery())
            total = await session.scalar(count_query) or 0

            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            return result.scalars().all(), total
