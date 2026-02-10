ncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import async_session_maker
from app.models.specialist import Specialist

async def seed_data():
    async with async_session_maker() as db:
        # Очищення старих даних (опціонально)
        from sqlalchemy import delete
        await db.execute(delete(Specialist))
        
        specialists = [
            Specialist(
                name="Ігор Зцілення",
                service_type="healer",
                delivery_method="human",
                specialty="Енергопрактик",
                hourly_rate=800,
                is_active=True
            ),
            Specialist(
                name="Nexus 3D Bot",
                service_type="visual3d",
                delivery_method="fully_ai",
                specialty="3D Моделювання",
                hourly_rate=150,
                is_active=True
            ),
            Specialist(
                name="Богдан Затишна Оселя",
                service_type="renovation",
                delivery_method="human",
                specialty="Майстер ремонту",
                hourly_rate=500,
                is_active=True
            )
        ]
        db.add_all(specialists)
        await db.commit()
        print("✅ Дані успішно завантажено!")

if __name__ == "__main__":
    asyncio.run(seed_data())
