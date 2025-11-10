from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy import select, update, func, desc
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
                "model_slug": task_data["model"],
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

    async def get_tasks_by_user_id_paginated(
            self,
            user_id: int,
            page: int = 1,
            limit: int = 20,
            model_name: Optional[str] = None
    ) -> Tuple[List[GenerationTask], int]:

        if page < 1:
            page = 1
        if limit < 1:
            limit = 20

        offset = (page - 1) * limit

        async with self.session_factory() as session:

            where_conditions = [GenerationTask.user_id == user_id]
            if model_name:
                where_conditions.append(GenerationTask.model_slug == model_name)

            stmt_tasks = (
                select(GenerationTask)
                .where(*where_conditions)
                .order_by(desc(GenerationTask.created_at))
                .offset(offset)
                .limit(limit)
            )

            result_tasks = await session.execute(stmt_tasks)
            tasks = result_tasks.scalars().all()

            stmt_count = (
                select(func.count(GenerationTask.id))
                .where(*where_conditions)
            )

            result_count = await session.scalar(stmt_count)
            total = result_count or 0

            return tasks, total