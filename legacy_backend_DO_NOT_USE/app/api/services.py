"""
API роутер для послуг (services)

Endpoints:
- GET /api/services - список доступних послуг
- GET /api/services/trending - топ послуг за попитом
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import logging

from app.database.connection import get_db
from app.models.specialist import Specialist
from app.schemas.responses import ServicesListResponse, ServiceInfo
from app.services.simple_analytics import analytics

logger = logging.getLogger(__name__)

# ✅ КРИТИЧНО: Об'єкт має називатися "router"
router = APIRouter()

# Каталог сервісів платформи
SERVICE_CATALOG = {
    "healer": {
        "name": "Енергопрактики",
        "icon": "🧘‍♀️",
        "description": "Духовні цілителі, майстри Рейкі, енергетичні практики"
    },
    "coach": {
        "name": "Коучі",
        "icon": "🌱",
        "description": "Особистісний розвиток, досягнення цілей, life coaching"
    },
    "teacher_math": {
        "name": "Вчителі математики",
        "icon": "📐",
        "description": "Репетитори з математики, підготовка до іспитів"
    },
    "teacher_ukrainian": {
        "name": "Вчителі української мови",
        "icon": "✍️",
        "description": "Репетитори української, підготовка до НМТ"
    },
    "teacher_english": {
        "name": "Вчителі англійської",
        "icon": "🇬🇧",
        "description": "Викладачі англійської мови, розмовна практика"
    },
    "web_development": {
        "name": "Веб-розробники",
        "icon": "💻",
        "description": "Створення сайтів, веб-додатків, API"
    },
    "3d_modeling": {
        "name": "3D-моделери",
        "icon": "🎨",
        "description": "3D-графіка, анімація, візуалізація"
    },
    "interior_design": {
        "name": "Дизайнери інтер'єрів",
        "icon": "🏡",
        "description": "Проектування приміщень, 3D-візуалізація інтер'єрів"
    },
    "ai_automation": {
        "name": "AI-експерти",
        "icon": "🤖",
        "description": "Автоматизація з використанням AI, чат-боти"
    },
    "smm": {
        "name": "SMM-спеціалісти",
        "icon": "📱",
        "description": "Просування в соціальних мережах"
    },
    "copywriting": {
        "name": "Копірайтери",
        "icon": "✍️",
        "description": "Створення текстового контенту"
    },
    "seo": {
        "name": "SEO-експерти",
        "icon": "🔍",
        "description": "Просування сайтів у пошукових системах"
    },
    "video_editing": {
        "name": "Відеомонтажери",
        "icon": "🎬",
        "description": "Монтаж та обробка відео"
    },
    "photo_editing": {
        "name": "Ретушери",
        "icon": "📷",
        "description": "Обробка та ретуш фотографій"
    }
}


@router.get(
    "/services",
    response_model=ServicesListResponse,
    summary="Отримати список послуг",
    description="Повертає каталог усіх доступних послуг з кількістю активних спеціалістів"
)
async def get_services(db: AsyncSession = Depends(get_db)):
    """
    Endpoint для отримання списку сервісів.
    
    Для кожного сервісу підраховує кількість активних спеціалістів у БД.
    """
    services_list = []
    
    for service_id, info in SERVICE_CATALOG.items():
        try:
            # Підрахунок активних спеціалістів
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
        except Exception as e:
            logger.error(f"❌ Error counting specialists for {service_id}: {e}")
            # Додаємо сервіс навіть якщо виникла помилка
            services_list.append(
                ServiceInfo(
                    id=service_id,
                    name=info["name"],
                    description=info["description"],
                    icon=info["icon"],
                    available_specialists=0
                )
            )
    
    return ServicesListResponse(
        services=services_list,
        total=len(services_list)
    )


@router.get(
    "/services/trending",
    summary="Топ послуг за попитом",
    description="Повертає найпопулярніші послуги на основі аналітики пошуків"
)
async def get_trending_services():
    """
    Endpoint для отримання трендових послуг.
    Використовує SimpleAnalytics.get_trending_services (demand за логами пошуків).
    """
    try:
        trending = analytics.get_trending_services(top_n=5)
        return {
            "status": "success",
            "trending": trending,
            "period": "last_7_days",
        }
    except Exception as e:
        logger.error("❌ Error fetching trending: %s", e, exc_info=True)
        return {
            "status": "error",
            "trending": [],
            "error": str(e),
        }
