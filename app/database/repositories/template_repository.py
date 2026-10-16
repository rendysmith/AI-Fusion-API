"""Video template data access repository."""

from sqlalchemy import select, asc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional

from app.database.video_template_models import VideoTemplate
from app.schemas import VideoTemplateCreate, VideoTemplateUpdate


class TemplateRepository:
    """Repository for VideoTemplate operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_by_id(self, template_id: int) -> Optional[VideoTemplate]:
        """Get a template by its ID."""
        async with self.session_factory() as session:
            return await session.get(VideoTemplate, template_id)

    async def get_all(self) -> List[VideoTemplate]:
        """Get all templates ordered by row and position."""
        async with self.session_factory() as session:
            stmt = select(VideoTemplate).order_by(
                asc(VideoTemplate.row_number),
                asc(VideoTemplate.position),
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create(self, payload: VideoTemplateCreate) -> VideoTemplate:
        """Create a new video template."""
        async with self.session_factory() as session:
            db_template = VideoTemplate(**payload.model_dump())
            session.add(db_template)
            await session.commit()
            await session.refresh(db_template)
            return db_template

    async def update(
        self, template_id: int, payload: VideoTemplateUpdate,
    ) -> Optional[VideoTemplate]:
        """Update an existing video template."""
        async with self.session_factory() as session:
            template = await session.get(VideoTemplate, template_id)
            if not template:
                return None

            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(template, key, value)

            await session.commit()
            await session.refresh(template)
            return template

    async def delete(self, template_id: int) -> bool:
        """Delete a video template by its ID."""
        async with self.session_factory() as session:
            template = await session.get(VideoTemplate, template_id)
            if not template:
                return False

            await session.delete(template)
            await session.commit()
            return True
