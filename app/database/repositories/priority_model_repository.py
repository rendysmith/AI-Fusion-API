import json
from sqlalchemy import select, update, delete, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional

from app.database.ai_model import PriorityModel, ChatSession, ChatMessage
from app.schemas import AiModelCreate, AiModelUpdate
from app.schemas.ai_model import ChatSessionCreate, ChatMessageCreate


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

    async def create_session(self, payload: ChatSessionCreate) -> ChatSession:
        """Создает новую сессию чата в таблице chat_sessions."""
        async with self.session_factory() as session:
            # Создаем экземпляр модели из схемы Pydantic
            db_session = ChatSession(
                user_id=payload.user_id,
                model_slug=payload.model_slug,
                chat_name=payload.chat_name
            )

            session.add(db_session)
            await session.commit()
            await session.refresh(db_session)
            return db_session

    async def create_message(self, payload: ChatMessageCreate) -> ChatMessage:
        """Создает новое сообщение в таблице chat_messages."""
        async with self.session_factory() as session:
            try:
                # Создаем экземпляр модели из схемы Pydantic
                db_message = ChatMessage(
                    session_id=payload.session_id,
                    role=payload.role,
                    message_text=payload.message_text,
                    token_count=payload.token_count
                )

                session.add(db_message)
                await session.commit()
                await session.refresh(db_message)
                return db_message
            except IntegrityError:
                await session.rollback()
                # Если session_id не существует, возникнет IntegrityError (Foreign Key violation)
                raise ValueError(f"Session with ID '{payload.session_id}' not found.")

    async def get_messages_by_session_id(self, session_id: int) -> List[ChatMessage]:
        """
        Получает все сообщения, принадлежащие конкретной сессии,
        отсортированные по времени создания (в порядке диалога).
        """
        async with self.session_factory() as session:
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(asc(ChatMessage.created_at))  # Сортировка по возрастанию времени
            )
            result = await session.execute(stmt)
            return result.scalars().all()



