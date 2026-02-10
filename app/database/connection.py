from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.models.base import Base  # ✅ Імпорт Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Ініціалізація бази даних"""
    # Імпортуємо всі моделі для create_all
    from app.models.user import User
    from app.models.message import Message
    from app.models.specialist import Specialist
    from app.models.specialist_content import SpecialistContent
    from app.models.conversation import Conversation
    from app.models.knowledge_base import KnowledgeBase

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ База даних ініціалізована")

async def get_db():
    """Dependency для FastAPI"""
    async with async_session_maker() as session:
        yield session
