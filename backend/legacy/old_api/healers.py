"""
Виправлені роутери для /health та /services
Тепер вони повертають структуровані JSON об'єкти замість "string"
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import time

from app.database.connection import get_db
from app.models.specialist import Specialist
from app.schemas.responses import (
    HealthResponse, 
    ServicesListResponse, 
    ServiceInfo
)
from app.ai.providers import get_ai_provider

# ============================================
# 🏥 HEALTH CHECK ROUTER
# ============================================
health_router = APIRouter()

# Зберігаємо час старту сервера
SERVER_START_TIME = time.time()

@health_router.get(
    "/health",
    response_model=HealthResponse,  # ✅ Тепер Swagger показує JSON структуру
    summary="Перевірка здоров'я системи",
    description="Повертає статус бази даних, AI провайдера та uptime"
)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Endpoint для моніторингу стану системи
    
    ✅ ВИПРАВЛЕНО: Замість "string" повертає HealthResponse
    """
    # Перевірка бази даних
    try:
        await db.execute(select(1))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    # Перевірка AI провайдера
    try:
        ai_provider = get_ai_provider()
        ai_status = "available" if ai_provider.gemini_available else "unavailable"
    except Exception:
        ai_status = "unavailable"
    
    # Розрахунок uptime
    uptime = time.time() - SERVER_START_TIME
    
    overall_status = "healthy" if (db_status == "connected" and ai_status == "available") else "degraded"
    
    return HealthResponse(
        status=overall_status,
        database=db_status,
        ai_provider=ai_status,
        uptime_seconds=round(uptime, 2)
    )


# ============================================
# 🎯 SERVICES ROUTER
# ============================================
services_router = APIRouter()

@services_router.get(
    "/services",
    response_model=ServicesListResponse,  # ✅ Тепер Swagger показує JSON структуру
    summary="Отримати список доступних послуг",
    description="Повертає каталог сервісів з кількістю доступних спеціалістів"
)
async def get_services(db: AsyncSession = Depends(get_db)):
    """
    Endpoint для отримання списку сервісів
    
    ✅ ВИПРАВЛЕНО: Замість "string" повертає ServicesListResponse
    """
    # Каталог сервісів
    SERVICE_CATALOG = {
        "healer": {"name": "Енергопрактики", "icon": "🧘‍♀️", "description": "Духовні цілителі та майстри енергії"},
        "coach": {"name": "Коучі", "icon": "🌱", "description": "Особистісний розвиток та досягнення цілей"},
        "teacher_math": {"name": "Вчителі математики", "icon": "📐", "description": "Репетитори з математики"},
        "teacher_ukrainian": {"name": "Вчителі української мови", "icon": "✍️", "description": "Репетитори української"},
        "teacher_english": {"name": "Вчителі англійської", "icon": "🇬🇧", "description": "Викладачі англійської мови"},
        "web_development": {"name": "Веб-розробники", "icon": "💻", "description": "Створення сайтів та додатків"},
        "3d_modeling": {"name": "3D-моделери", "icon": "🎨", "description": "3D-графіка та анімація"},
        "interior_design": {"name": "Дизайнери інтер'єрів", "icon": "🏡", "description": "Проектування приміщень"},
        "ai_automation": {"name": "AI-експерти", "icon": "🤖", "description": "Автоматизація з AI"},
        "smm": {"name": "SMM-спеціалісти", "icon": "📱", "description": "Просування в соцмережах"},
        "copywriting": {"name": "Копірайтери", "icon": "✍️", "description": "Створення текстового контенту"},
    }
    
    services_list = []
    
    for service_id, info in SERVICE_CATALOG.items():
        # Підраховуємо кількість активних спеціалістів
        result = await db.execute(
            select(func.count(Specialist.id))
            .where(
                Specialist.service_type == service_id,
                Specialist.is_active == True
            )
        )
        count = result.scalar() or 0
        
        services_list.append(
            ServiceInfo(
                id=service_id,
                name=info["name"],
                description=info["description"],
                icon=info["icon"],
                available_specialists=count
            )
        )
    
    return ServicesListResponse(
        services=services_list,
        total=len(services_list)
    )


# ============================================
# ЕКСПОРТ РОУТЕРІВ
# ============================================
# У main.py імпортуйте так:
# from app.api.health import health_router, services_router
# app.include_router(health_router, prefix="/api", tags=["System"])
# app.include_router(services_router, prefix="/api", tags=["Services"])
