import json
from sqlalchemy import select, update, delete, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional

from app.database.ai_model import AiModel
from app.schemas import AiModelCreate, AiModelUpdate


class AiModelRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_by_id(self, model_id: int) -> Optional[AiModel]:
        async with self.session_factory() as session:
            return await session.get(AiModel, model_id)

    async def get_by_slug(self, slug: str) -> Optional[AiModel]:
        async with self.session_factory() as session:
            stmt = select(AiModel).where(AiModel.slug == slug)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_all_by_category(self, category: Optional[str] = None) -> List[AiModel]:
        async with self.session_factory() as session:
            stmt = select(AiModel).order_by(asc(AiModel.sort_order))  # (snake_case)
            if category:
                stmt = stmt.where(AiModel.category == category)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def create(self, payload: AiModelCreate) -> AiModel:
        async with self.session_factory() as session:
            try:
                settings_dict = json.loads(payload.settings) if payload.settings else None

                db_model = AiModel(
                    **payload.dict(exclude={'settings'}),
                    settings=settings_dict
                )
                session.add(db_model)
                await session.commit()
                await session.refresh(db_model)
                return db_model
            except IntegrityError:
                await session.rollback()
                raise ValueError(f"Model with slug '{payload.slug}' already exists")

    async def update(self, model_id: int, payload: AiModelUpdate) -> Optional[AiModel]:
        async with self.session_factory() as session:
            model = await session.get(AiModel, model_id)
            if not model:
                return None

            update_data = payload.dict(exclude_unset=True)

            if 'settings' in update_data and isinstance(update_data['settings'], str):
                update_data['settings'] = json.loads(update_data['settings'])

            for key, value in update_data.items():
                setattr(model, key, value)

            try:
                await session.commit()
                await session.refresh(model)
                return model
            except IntegrityError:
                await session.rollback()
                raise ValueError(f"Model with slug '{payload.slug}' already exists")

    async def delete(self, model_id: int) -> bool:
        async with self.session_factory() as session:
            model = await session.get(AiModel, model_id)
            if not model:
                return False

            await session.delete(model)
            await session.commit()
            return True