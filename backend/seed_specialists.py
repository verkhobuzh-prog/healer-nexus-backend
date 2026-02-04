import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.models.specialist import Specialist
from app.models.base import Base
from app.config import settings

async def seed():
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        # ПРИМУСОВО ВИДАЛЯЄМО І СТВОРЮЄМО ТАБЛИЦІ
        await conn.execute(text("DROP TABLE IF EXISTS specialists CASCADE;"))
        await conn.run_sync(Base.metadata.create_all)
        print("📁 Таблиці перестворено з нуля!")

    async with async_session() as session:
        s1 = Specialist(
            name="Олексій", 
            niche="repair", 
            specialty="furniture", 
            bio="Майстер по дереву, реставратор меблів.",
            hourly_rate=500,
            is_verified=True
        )
        s2 = Specialist(
            name="Олена", 
            niche="teacher", 
            specialty="yoga", 
            bio="Інструктор з хатха-йоги.",
            hourly_rate=800,
            is_verified=False
        )
        
        session.add_all([s1, s2])
        await session.commit()
        print("✅ Дані успішно додані в нову структуру!")

if __name__ == "__main__":
    asyncio.run(seed())
