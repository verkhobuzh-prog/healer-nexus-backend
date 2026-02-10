from database.connection import engine, Base
# Імпортуємо всі моделі, щоб SQLAlchemy знав про їх існування
from app.models.user import User
from app.models.healer import Healer
from app.models.booking import Booking
from app.models.agent import AgentDecision, AgentMetric, AgentAlert

async def init_database():
    """Створення всіх таблиць на основі моделей SQLAlchemy"""
    async with engine.begin() as conn:
        # В режимі розробки ми можемо перестворювати таблиці
        # await conn.run_sync(Base.metadata.drop_all) 
        
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")
