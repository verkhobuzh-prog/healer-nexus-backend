from sqlalchemy import select
from app.database.connection import get_db
from app.models.message import Message  # ✅ Коректний шлях
from app.models.user import User        # ✅ Коректний шлях

class MemoryService:
    @staticmethod
    async def get_user_context(user_id: int, limit: int = 5):
        """Отримує останні N повідомлень для контексту"""
        async with get_db() as session:
            query = (
                select(Message)
                .where(Message.user_id == user_id)
                .order_by(Message.id.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            messages = result.scalars().all()
            
            # Повертаємо історію: від старіших до новіших
            return [{"role": m.role, "content": m.content} for m in reversed(messages)]

    @staticmethod
    async def add_to_memory(user_id: int, role: str, content: str):
        """Зберігає повідомлення в базу"""
        async with get_db() as session:
            new_msg = Message(user_id=user_id, role=role, content=content)
            session.add(new_msg)
            await session.commit()
