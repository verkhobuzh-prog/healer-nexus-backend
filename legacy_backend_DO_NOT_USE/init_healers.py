import asyncio
from sqlalchemy import text
# Імпортуємо налаштування прямо з твого додатка
from app.database import engine, async_session_maker

async def init_db():
    print("🚀 Починаю підготовку бази даних...")
    
    async with engine.begin() as conn:
        # Створюємо таблицю healers
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS healers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                specialty VARCHAR(255),
                bio TEXT,
                phone VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("✅ Таблиця 'healers' створена або вже існує.")

    async with async_session_maker() as session:
        # Додаємо тестового фахівця, щоб Агенту було що аналізувати
        await session.execute(text("""
            INSERT INTO healers (name, specialty, bio, phone) 
            VALUES ('Доктор Олексій', 'Психотерапевт', 'Спеціаліст з когнітивної психології та розладів сну', '+380991112233')
            ON CONFLICT DO NOTHING;
        """))
        await session.commit()
        print("✅ Тестовий фахівець успішно доданий.")

if __name__ == "__main__":
    asyncio.run(init_db())
