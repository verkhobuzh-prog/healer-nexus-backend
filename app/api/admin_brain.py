"""
AI Brain monitoring for admin: health, insights.
GET /api/admin/brain/health, GET /api/admin/brain/insights.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.connection import get_db
from app.ai.brain.brain_core import AIBrainCore
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/brain", tags=["Admin Brain"])


@router.get("/health")
async def brain_health() -> dict[str, Any]:
    """
    Стан AI Brain: наявність ключа, компоненти (RoleSwitcher, HybridProvider).
    """
    gemini_ok = bool(getattr(settings, "GEMINI_API_KEY", None))
    try:
        core = AIBrainCore()
        role_switcher_ok = core.role_switcher is not None
        hybrid_ok = core.hybrid_provider is not None
        knowledge_ok = core.knowledge_manager is not None
    except Exception as e:
        logger.warning("Admin brain health check: %s", e)
        role_switcher_ok = hybrid_ok = knowledge_ok = False

    return {
        "status": "ok" if (gemini_ok and hybrid_ok) else "degraded",
        "checks": {
            "gemini_api_key": gemini_ok,
            "role_switcher": role_switcher_ok,
            "hybrid_provider": hybrid_ok,
            "knowledge_manager": knowledge_ok,
        },
    }


@router.get("/insights")
async def brain_insights(
    service_type: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Інсайти AI Brain: з KnowledgeManager (in-memory) та агрегати по розмовах з БД.
    """
    try:
        core = AIBrainCore()
        km = core.knowledge_manager
        latest = km.get_latest(limit=limit) if service_type is None else km.get_insights(service_type)
        if service_type and len(latest) > limit:
            latest = latest[-limit:]
        elif not service_type and len(latest) > limit:
            latest = latest[-limit:]
    except Exception as e:
        logger.warning("Admin brain insights (KnowledgeManager): %s", e)
        latest = []

    # Агрегати з Conversation
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    try:
        total = await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.project_id == project_id,
                Conversation.deleted_at.is_(None),
            )
        )
        total_conversations = total.scalar() or 0
        converted = await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.project_id == project_id,
                Conversation.deleted_at.is_(None),
                Conversation.converted == True,
            )
        )
        converted_count = converted.scalar() or 0
    except Exception as e:
        logger.warning("Admin brain insights (DB): %s", e)
        total_conversations = converted_count = 0

    return {
        "insights": latest,
        "summary": {
            "total_conversations": total_conversations,
            "converted": converted_count,
            "project_id": project_id,
        },
    }
