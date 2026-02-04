import asyncio
from app.database.connection import async_session_maker
from app.models.specialist import Specialist

async def seed():
    specialists = [
        Specialist(
            name="Богдан", niche="healer", specialty="Терапевт", 
            bio="Допомагаю знайти внутрішній спокій.", hourly_rate=1200
        ),
        Specialist(
            name="Олександр", niche="artist", specialty="Художник-портретист", 
            bio="Малюю живі портрети олією.", hourly_rate=800
        ),
        Specialist(
            name="Тетяна", niche="education", specialty="Вчитель англійської", 
            bio="Англійська для IT та бізнесу.", hourly_rate=500
        )
    ]
    
    async with async_session_maker() as session:
        session.add_all(specialists)
        await session.commit()
    print("✅ База наповнена спеціалістами!")

if __name__ == "__main__":
    asyncio.run(seed())
