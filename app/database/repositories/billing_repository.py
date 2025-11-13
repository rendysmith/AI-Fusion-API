import uuid
from sqlalchemy import select, update, Row, RowMapping, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional, Any, Coroutine, Sequence
from app.database.billing_models import Product, Payment, PaymentInvoice


class BillingRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_product(self, product_id: int) -> Optional[Product]:
        async with self.session_factory() as session:
            return await session.get(Product, product_id)

    async def get_all_products(self) -> Sequence[Product]:
        async with self.session_factory() as session:

            stmt = select(Product).where(Product.is_active == True).order_by(Product.sort_order)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create_payment(self, user_id: int, product_id: int, amount: int, provider: str,
                             external_id: str) -> Payment:
        async with self.session_factory() as session:
            payment = Payment(
                internal_id=f"pay_{uuid.uuid4().hex}",
                user_id=user_id,
                product_id=product_id,
                amount=amount,
                provider=provider,
                external_payment_id=external_id,
                status="pending"
            )
            session.add(payment)
            await session.commit()
            await session.refresh(payment)
            return payment

    async def get_payment_by_external_id(self, external_id: str) -> Optional[Payment]:
        async with self.session_factory() as session:
            stmt = select(Payment).where(Payment.external_payment_id == external_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def complete_payment(self, internal_id: str):
        async with self.session_factory() as session:
            await session.execute(
                update(Payment)
                .where(Payment.internal_id == internal_id)
                .values(status="completed")
            )
            await session.commit()

    async def create_invoice(self, payment: Payment):
        async with self.session_factory() as session:
            invoice = PaymentInvoice(
                user_id=payment.user_id,
                payment_id=payment.internal_id,
                amount=payment.amount,
                status="paid",
                paid_at=func.now()
            )
            session.add(invoice)
            await session.commit()

    async def get_user_invoices(self, user_id: int, limit: int, offset: int) -> Sequence[PaymentInvoice]:

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

    async def get_payment_by_internal_id(self, internal_id: str) -> Optional[Payment]:

        async with self.session_factory() as session:
            return await session.get(Payment, internal_id)