"""Chat session and message data access repository."""

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import List, Optional

from app.database.chat import ChatSession, ChatMessage
from app.schemas import ChatSessionCreate, ChatMessageCreate


class ChatRepository:
    """Repository for ChatSession and ChatMessage operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def create_session(self, payload: ChatSessionCreate) -> ChatSession:
        """Create a new chat session."""
        async with self.session_factory() as session:
            new_session = ChatSession(
                user_id=payload.user_id,
                model_slug=payload.model_slug,
                chat_name=payload.chat_name,
            )
            session.add(new_session)
            await session.commit()
            await session.refresh(new_session)
            return new_session

    async def get_session_by_id(self, session_id: int) -> Optional[ChatSession]:
        """Get a chat session by its ID."""
        async with self.session_factory() as session:
            return await session.get(ChatSession, session_id)

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """Get all chat sessions for a user."""
        async with self.session_factory() as session:
            stmt = (
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(desc(ChatSession.updated_at))
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def delete_session(self, session_id: int, user_id: int) -> bool:
        """Delete a chat session belonging to a user."""
        async with self.session_factory() as session:
            stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
            result = await session.execute(stmt)
            obj = result.scalars().first()
            if not obj:
                return False
            await session.delete(obj)
            await session.commit()
            return True

    async def create_message(self, payload: ChatMessageCreate) -> ChatMessage:
        """Create a new chat message."""
        async with self.session_factory() as session:
            msg = ChatMessage(**payload.model_dump())
            session.add(msg)
            await session.commit()
            return msg

    async def get_messages_by_session_id(
        self, session_id: int,
    ) -> List[ChatMessage]:
        """Get all messages for a chat session."""
        async with self.session_factory() as session:
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
