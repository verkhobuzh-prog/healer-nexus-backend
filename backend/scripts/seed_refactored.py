import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import async_session_maker, init_db
from app.models.specialist import Specialist

async def seed_data():
    print("🚀 Starting database seeding...")
    # Ініціалізація таблиць, якщо вони не створені
    await init_db()

    async with async_session_maker() as session:
        # Створюємо список об'єктів
        specialists = [
            Specialist(
                name="Богдан",
                service_type="interior_design",
                specialty="Дизайнер інтер'єру, проектування, установка меблів — повний цикл",
                delivery_method="human",
                hourly_rate=800,
                is_active=True,
                is_ai_powered=False
            ),
            Specialist(
                name="Лариса",
                service_type="teacher_ukrainian", # Залишаємо цей тип для синьої теми
                specialty="Вчитель української мови та математики (4-7 класи). Досвід 30 років, наявні рекомендації",
                delivery_method="human",
                hourly_rate=450,
                is_active=True,
                is_ai_powered=False
            ),
            Specialist(
                name="Таня",
                service_type="teacher_math",
                specialty="Вчитель математики (алгебра, геометрія) 5-11 класи",
                delivery_method="human",
                hourly_rate=500,
                is_active=True,
                is_ai_powered=False
            ),
            Specialist(
                name="Олексій AI",
                service_type="ai_automation",
                specialty="AI автоматизація, розробка чат-ботів, інтеграція нейромереж",
                delivery_method="human",
                hourly_rate=2500,
                is_active=True,
                is_ai_powered=False
            ),
            Specialist(
                name="Максим Web",
                service_type="web_development",
                specialty="Web розробка, інтерактивні сайти, Frontend/Backend",
                delivery_method="human",
                hourly_rate=1800,
                is_active=True,
                is_ai_powered=False
            ),
            Specialist(
                name="Надя",
                service_type="coach",
                specialty="Трансформаційний коучинг, особистісний розвиток",
                delivery_method="ai_assisted",
                hourly_rate=2000,
                is_active=True,
                is_ai_powered=True
            ),
            Specialist(
                name="Ігор",
                service_type="healer",
                specialty="Енергопрактики, біоенергетика, цілительство",
                delivery_method="human",
                hourly_rate=1800,
                is_active=True,
                is_ai_powered=False
            ),
            Specialist(
                name="Антон",
                service_type="healer",
                specialty="Цілитель, регресолог, кармолог",
                delivery_method="human",
                hourly_rate=2000,
                is_active=True,
                is_ai_powered=False
            ),
            Specialist(
                name="Nexus AI",
                service_type="general",
                specialty="Універсальний AI помічник",
                delivery_method="fully_ai",
                hourly_rate=0,
                is_active=True,
                is_ai_powered=True
            )
        ]

        # Додаємо всіх за один раз
        session.add_all(specialists)
        # Фіксуємо зміни
        await session.commit()
    print(f"✅ Database successfully seeded with {len(specialists)} specialists!")

if __name__ == "__main__":
    asyncio.run(seed_data())
