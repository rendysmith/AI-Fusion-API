"""AI model data access repository."""

from sqlalchemy import select, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional

from app.database.ai import AiModel
from app.schemas import AiModelCreate, AiModelUpdate


class AiModelRepository:
    """Repository for AiModel operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_by_id(self, model_id: int) -> Optional[AiModel]:
        """Get an AI model by its ID."""
        async with self.session_factory() as session:
            return await session.get(AiModel, model_id)

    async def get_by_slug(self, slug: str) -> Optional[AiModel]:
        """Get an AI model by its slug."""
        async with self.session_factory() as session:
            stmt = select(AiModel).where(AiModel.slug == slug)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_proveder_all(self, description: str) -> Optional[AiModel]:
        """Get AI models by description ordered by sort_order."""
        async with self.session_factory() as session:
            stmt = (
                select(AiModel)
                .where(AiModel.description == description)
                .order_by(asc(AiModel.sort_order))
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_by_name(self, name: str) -> Optional[AiModel]:
        """Get an AI model by its name."""
        async with self.session_factory() as session:
            stmt = select(AiModel).where(AiModel.name == name)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_all_by_category(self, category: Optional[str] = None) -> List[AiModel]:
        """Get all AI models, optionally filtered by category."""
        async with self.session_factory() as session:
            stmt = select(AiModel).order_by(asc(AiModel.sort_order))
            if category:
                stmt = stmt.where(AiModel.category == category)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def create(self, payload: AiModelCreate) -> AiModel:
        """Create a new AI model."""
        async with self.session_factory() as session:
            try:
                data = payload.model_dump(exclude={"settings"})

                db_model = AiModel(**data, settings=payload.settings)
                session.add(db_model)
                await session.commit()
                await session.refresh(db_model)
                return db_model
            except IntegrityError:
                await session.rollback()
                raise ValueError(f"Model with slug '{payload.slug}' already exists")

    async def update(self, model_id: int, payload: AiModelUpdate) -> Optional[AiModel]:
        """Update an existing AI model."""
        async with self.session_factory() as session:
            model = await session.get(AiModel, model_id)
            if not model:
                return None

            update_data = payload.model_dump(exclude_unset=True)

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
        """Delete an AI model by its ID."""
        async with self.session_factory() as session:
            model = await session.get(AiModel, model_id)
            if not model:
                return False

            await session.delete(model)
            await session.commit()
            return True
