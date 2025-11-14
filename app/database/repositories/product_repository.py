from sqlalchemy import select, asc, Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional, Any, Coroutine, Sequence

from app.database.billing_models import Product
from app.schemas import ProductCreate, ProductUpdate


class ProductRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_all(self, only_active: bool = False) -> Sequence[Product]:

        async with self.session_factory() as session:
            stmt = select(Product).order_by(asc(Product.sort_order))

            if only_active:
                stmt = stmt.where(Product.is_active == True)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        async with self.session_factory() as session:
            return await session.get(Product, product_id)

    async def create(self, payload: ProductCreate) -> Product:
        async with self.session_factory() as session:

            db_product = Product(**payload.model_dump())
            session.add(db_product)
            await session.commit()
            await session.refresh(db_product)
            return db_product

    async def update(self, product_id: int, payload: ProductUpdate) -> type[Product] | None:
        async with self.session_factory() as session:
            product = await session.get(Product, product_id)
            if not product:
                return None

            update_data = payload.model_dump(exclude_unset=True)

            for key, value in update_data.items():
                setattr(product, key, value)

            await session.commit()
            await session.refresh(product)
            return product

    async def delete(self, product_id: int) -> bool:
        async with self.session_factory() as session:
            product = await session.get(Product, product_id)
            if not product:
                return False

            await session.delete(product)
            await session.commit()
            return True