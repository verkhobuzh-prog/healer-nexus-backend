"""
Healer Nexus — DB Service (message history)
Fixed: Uses shared async_session_maker from connection.py (single engine, single pool)
"""

from sqlalchemy import select

from app.database.connection import async_session_maker
from app.models.message import Message


async def save_message(user_id: int, role: str, content: str):
    """Save a new message to conversation history."""
    async with async_session_maker() as session:
        async with session.begin():
            new_msg = Message(user_id=user_id, role=role, content=content)
            session.add(new_msg)


async def get_history(user_id: int, limit: int = 10):
    """Get last N messages for AI context."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Message)
            .filter(Message.user_id == user_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        # Return oldest-first for conversation context
        return [{"role": m.role, "content": m.content} for m in reversed(messages)]