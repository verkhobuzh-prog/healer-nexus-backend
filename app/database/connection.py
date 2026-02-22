from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.models.base import Base  # ✅ Імпорт Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=(
        {"check_same_thread": False, "timeout": 30}
        if "sqlite" in settings.DATABASE_URL.lower()
        else {}
    ),
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Ініціалізація бази даних — імпортуємо всі моделі перед create_all."""
    from app.models.user import User  # noqa: F401
    from app.models.message import Message  # noqa: F401
    from app.models.specialist import Specialist  # noqa: F401
    from app.models.specialist_content import SpecialistContent  # noqa: F401
    from app.models.conversation import Conversation  # noqa: F401
    from app.models.knowledge_base import KnowledgeBase  # noqa: F401
    from app.models.refresh_token import RefreshToken  # noqa: F401
    from app.models.specialist_recommendation import SpecialistRecommendation  # noqa: F401
    from app.models.practitioner_profile import PractitionerProfile  # noqa: F401
    from app.models.booking import Booking  # noqa: F401
    from app.models.blog_post import BlogPost  # noqa: F401
    from app.models.blog_category import BlogCategory  # noqa: F401
    from app.models.blog_tag import BlogTag  # noqa: F401
    from app.models.blog_post_tag import BlogPostTag  # noqa: F401
    from app.models.blog_post_view import BlogPostView  # noqa: F401
    from app.models.blog_analytics_daily import BlogAnalyticsDaily  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ База даних ініціалізована")

async def get_db():
    """Dependency для FastAPI"""
    async with async_session_maker() as session:
        yield session
