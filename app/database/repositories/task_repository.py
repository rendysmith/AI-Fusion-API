from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.task_models import GenerationTask


class TaskRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_task(self, task_id: str) -> Optional[GenerationTask]:

        async with self.session_factory() as session:
            return await session.get(GenerationTask, task_id)

    async def upsert_and_start_task(
            self,
            task_data: Dict[str, Any],
            worker_id: str
    ) -> Optional[GenerationTask]:

        async with self.session_factory() as session:

            insert_values = {
                "id": task_data["_id"],
                "user_id": task_data["user_id"],
                "model_name": task_data["model"],
                "params": task_data.get("params", {}),
                "cost": task_data.get("cost"),
                "prime_cost": task_data.get("prime_cost"),
                "created_at": datetime.fromisoformat(task_data["created_at"]),
                "status": "processing",
                "processed_by": worker_id,
                "result": None,
                "error": None
            }


            stmt = pg_insert(GenerationTask).values(**insert_values)

            on_conflict_stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_={
                    "status": "processing",
                    "processed_by": worker_id,
                    "result": None,
                    "error": None,
                    "updated_at": func.now()
                }
            )

            await session.execute(on_conflict_stmt)
            await session.commit()


            return await self.get_task(task_data["_id"])

    async def complete_task(self, task_id: str, result_data: Dict[str, Any]):

        async with self.session_factory() as session:
            stmt = (
                update(GenerationTask)
                .where(GenerationTask.id == task_id)
                .values(
                    status="completed",
                    result=result_data,
                    error=None,
                    updated_at=func.now()
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def fail_task(self, task_id: str, error_message: str):

        async with self.session_factory() as session:
            stmt = (
                update(GenerationTask)
                .where(GenerationTask.id == task_id)
                .values(
                    status="failed",
                    error=error_message,
                    result=None,
                    updated_at=func.now()
                )
            )
            await session.execute(stmt)
            await session.commit()