from fastapi import APIRouter
from typing import Dict, Any

from app.core.module_registry import get_registry

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Перевірка здоров'я всієї системи.
    
    Збирає health checks від всіх зареєстрованих модулів
    та повертає агрегований статус.
    
    Returns:
        dict: {
            "overall": "healthy" | "degraded" | "down",
            "modules": {...},
            "summary": {...}
        }
    """
    registry = get_registry()
    return await registry.get_overall_status()

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Метрики всіх модулів системи.
    
    Returns:
        dict: Метрики від кожного модуля
    """
    registry = get_registry()
    return await registry.get_all_metrics()

@router.get("/analytics")
async def get_analytics() -> Dict[str, Any]:
    """
    Аналітика попиту на послуги.
    
    Returns:
        dict: {
            "trending": [...],
            "demand_7d": {...}
        }
    """
    from app.services.simple_analytics import analytics
    
    return {
        "trending": analytics.get_trending_services(top_n=5),
        "demand_7d": analytics.get_all_demand()
    }
