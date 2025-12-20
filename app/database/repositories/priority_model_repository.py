from sqlalchemy import select, asc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional

from app.database.ai import PriorityModel
from app.schemas import BackendCreate, BackendUpdate


class PriorityModelRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_by_proveder_all(self, model_name: str) -> Optional[PriorityModel]:
        async with self.session_factory() as session:
            stmt = (
                select(PriorityModel)
                .where(PriorityModel.model_name == model_name)
                .order_by(asc(PriorityModel.sort_priority))
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_all_backends(self) -> List[PriorityModel]:
        async with self.session_factory() as session:
            stmt = select(PriorityModel).order_by(PriorityModel.model_name, PriorityModel.sort_priority)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create_backend(self, payload: BackendCreate) -> PriorityModel:
        async with self.session_factory() as session:
            db_obj = PriorityModel(**payload.model_dump())
            session.add(db_obj)
            await session.commit()
            await session.refresh(db_obj)
            return db_obj

    async def update_backend(self, backend_id: int, payload: BackendUpdate) -> Optional[PriorityModel]:
        async with self.session_factory() as session:
            obj = await session.get(PriorityModel, backend_id)
            if not obj:
                return None

            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(obj, key, value)

            await session.commit()
            await session.refresh(obj)
            return obj

    async def delete_backend(self, backend_id: int) -> bool:
        async with self.session_factory() as session:
            obj = await session.get(PriorityModel, backend_id)
            if not obj:
                return False
            await session.delete(obj)
            await session.commit()
            return True


