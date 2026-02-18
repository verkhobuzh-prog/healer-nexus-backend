"""Dashboard API endpoints - statistics and metrics for admin panel."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
import logging

from app.database.connection import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.specialist import Specialist
from app.config import settings

router = APIRouter(tags=["dashboard"])
logger = logging.getLogger(__name__)


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get overall platform statistics."""
    # Total users (User model has no project_id)
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar() or 0

    # Total conversations (filter by project_id)
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    convs_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.project_id == project_id)
    )
    total_conversations = convs_result.scalar() or 0

    # Total messages (Message has no project_id)
    msgs_result = await db.execute(select(func.count(Message.id)))
    total_messages = msgs_result.scalar() or 0

    # Active specialists (Specialist model has no project_id in this codebase)
    specialists_result = await db.execute(
        select(func.count(Specialist.id)).where(Specialist.is_active == True)
    )
    total_specialists = specialists_result.scalar() or 0

    # Last 7 days activity (conversations created)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.project_id == project_id,
            Conversation.created_at >= week_ago,
        )
    )
    active_last_week = recent_result.scalar() or 0

    return {
        "total_users": total_users,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_specialists": total_specialists,
        "active_last_week": active_last_week,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/specialists")
async def get_specialists_stats(db: AsyncSession = Depends(get_db)):
    """Get specialist statistics."""
    result = await db.execute(
        select(Specialist).where(Specialist.is_active == True)
    )
    specialists = result.scalars().all()

    return {
        "specialists": [
            {
                "id": s.id,
                "name": s.name,
                "specialty": s.specialty,
                "service_type": s.service_type,
                "hourly_rate": s.hourly_rate,
                "delivery_method": s.delivery_method,
                "is_ai_powered": s.is_ai_powered,
            }
            for s in specialists
        ],
        "count": len(specialists),
    }


@router.get("/recent-activity")
async def get_recent_activity(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get recent conversations."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()

    return {
        "recent_conversations": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in conversations
        ],
    }
