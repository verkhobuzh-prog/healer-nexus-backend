import asyncio
import sys
import os

# Налаштування шляхів
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import engine, Base
from app.models.user import User
from app.models.healer import Healer
from app.models.booking import Booking
from app.models.agent import AgentDecision, AgentMetric, AgentAlert
from app.models.system import SystemMetric

async def init_database():
    print("🚀 Початок ініціалізації бази даних...")
    try:
        async with engine.begin() as conn:
            # Це створить таблиці на основі всіх імпортованих моделей вище
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Всі таблиці успішно створені в PostgreSQL!")
    except Exception as e:
        print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    asyncio.run(init_database())
