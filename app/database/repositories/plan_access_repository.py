from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List

from app.database.billing_models import PlanModelAccess
from app.database.ai import AiModel
from app.schemas import PlanModelAccessCreate


class PlanAccessRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_all(self) -> List[PlanModelAccess]:
        async with self.session_factory() as session:
            stmt = select(PlanModelAccess)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create(self, payload: PlanModelAccessCreate) -> PlanModelAccess:

        async with self.session_factory() as session:
            try:
                db_access = PlanModelAccess(**payload.dict())
                session.add(db_access)
                await session.commit()
                await session.refresh(db_access)
                return db_access
            except IntegrityError:
                await session.rollback()
                raise ValueError("Access already exists for this plan and model")

    async def delete_by_plan_and_model(self, plan_id: int, model_id: int) -> bool:

        async with self.session_factory() as session:
            stmt = (
                delete(PlanModelAccess)
                .where(
                    PlanModelAccess.plan_id == plan_id,
                    PlanModelAccess.model_id == model_id
                )
                .returning(PlanModelAccess.id)
            )

            result = await session.scalar(stmt)
            await session.commit()

            return result is not None

    async def get_models_for_plan(self, plan_id: int) -> List[AiModel]:

        async with self.session_factory() as session:
            stmt = (
                select(AiModel)
                .join(PlanModelAccess, PlanModelAccess.model_id == AiModel.id)
                .where(PlanModelAccess.plan_id == plan_id)
                .where(AiModel.is_available == True)
            )
            result = await session.execute(stmt)
            return result.scalars().all()