from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.config import settings
from app.models.base import Base

# 1. Створюємо двигун (Engine)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    # Параметр для асинхронного SQLite
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 2. Сучасна фабрика сесій для SQLAlchemy 2.0
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Ініціалізація структури бази даних"""
    # Імпортуємо моделі, щоб Base побачив їх перед створенням таблиць
    # Зверніть увагу: Specialist тепер імпортується з base
    from app.models.user import User
    from app.models.message import Message
    from app.models.base import Specialist 

    async with engine.begin() as conn:
        # Створюємо всі зареєстровані таблиці
        await conn.run_sync(Base.metadata.create_all)

    db_type = "PostgreSQL" if "postgresql" in settings.DATABASE_URL else "SQLite"
    print(f"✅ База даних {db_type} синхронізована.")

# --- Функції бізнес-логіки (можна тримати тут або в db_service.py) ---

async def save_message(user_id: int, role: str, content: str):
    """Збереження нового повідомлення в історію"""
    from app.models.message import Message
    async with async_session_maker() as session:
        async with session.begin(): 
            new_msg = Message(user_id=user_id, role=role, content=content)
            session.add(new_msg)

async def get_history(user_id: int, limit: int = 10):
    """Отримання останніх повідомлень користувача для контексту AI"""
    from app.models.message import Message
    async with async_session_maker() as session:
        result = await session.execute(
            select(Message)
            .filter(Message.user_id == user_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        # Повертаємо історію від старого до нового
        return [{"role": m.role, "content": m.content} for m in reversed(messages)]
