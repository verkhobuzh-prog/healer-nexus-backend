from sqlalchemy import select
from app.config import settings
from app.database.connection import async_session_maker
from app.models.message import Message

class MemoryService:
    @staticmethod
    async def get_user_context(user_id: int, limit: int = 5):
        """Отримує останні N повідомлень для контексту (project_id from settings)."""
        async with async_session_maker() as session:
            query = (
                select(Message)
                .where(
                    Message.user_id == user_id,
                    Message.project_id == settings.PROJECT_ID,
                )
                .order_by(Message.id.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            messages = result.scalars().all()

            return [{"role": m.role, "content": m.content} for m in reversed(messages)]

    @staticmethod
    async def add_to_memory(user_id: int, role: str, content: str):
        """Зберігає повідомлення в базу (project_id from settings)."""
        async with async_session_maker() as session:
            new_msg = Message(
                project_id=settings.PROJECT_ID,
                user_id=user_id,
                role=role,
                content=content,
            )
            session.add(new_msg)
            await session.commit()
