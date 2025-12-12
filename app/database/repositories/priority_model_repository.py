import json
from sqlalchemy import select, update, delete, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional

from app.database.ai_model import PriorityModel
from app.schemas import AiModelCreate, AiModelUpdate


class PriorityModelRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_by_proveder_all(self, model_name: str) -> Optional[PriorityModel]:
        async with self.session_factory() as session:
            stmt = (
                select(PriorityModel)
                .where(PriorityModel.model_name == model_name)
                .order_by(asc(PriorityModel.sort_priority))  # Сортировка по sort_priority по возрастанию
            )
            result = await session.execute(stmt)
            return result.scalars().all()