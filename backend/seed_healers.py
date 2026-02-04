import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.specialist import Specialist
from app.config import settings

async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        healers = [
            Specialist(
                name="Марія Енерджі",
                specialty="Майстер Рейкі, Енергопрактик",
                service_type="healer",
                hourly_rate=1200,
                is_active=True,
                is_ai_powered=False,
                delivery_method="online"
            ),
            Specialist(
                name="Антон Дзен",
                specialty="Провідник у медитації",
                service_type="healer",
                hourly_rate=800,
                is_active=True,
                is_ai_powered=False,
                delivery_method="online"
            )
        ]
        session.add_all(healers)
        await session.commit()
        print("✅ Енергопрактики додані до бази!")

if __name__ == "__main__":
    asyncio.run(seed())
