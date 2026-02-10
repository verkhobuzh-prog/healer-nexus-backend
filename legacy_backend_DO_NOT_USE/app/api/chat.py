"""Chat API with AI primary path and specialist-search fallback when AI is unavailable."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.connection import get_db
from app.ai.providers import get_ai_provider
from app.models.specialist import Specialist
from app.schemas.responses import ChatResponse

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    history: list = []
    user_id: int = 0


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Відправити повідомлення AI асистенту",
    description="Генерує відповідь від AI; при недоступності AI — пошук спеціалістів за ключовими словами",
)
async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Primary: Gemini 1.5 Flash. Fallback: search specialists by keywords, return safe-mode response."""
    try:
        ai = get_ai_provider()
        result = await ai.generate_response(
            request.message,
            request.history or [],
            role="default",
        )
        return ChatResponse(
            response=result.get("text", ""),
            is_safe_mode=False,
            model_used="gemini-1.5-flash",
            suggestions=[],
        )
    except Exception as e:
        logger.error(
            "AI provider failed, activating safe mode fallback",
            exc_info=True,
            extra={
                "user_message": request.message,
                "error_type": type(e).__name__,
                "model": "gemini-1.5-flash",
            },
        )

        # Safe mode: search specialists by keywords
        keywords = request.message.lower().split()
        stop_words = {"я", "мені", "потрібен", "допоможіть", "знайти", "хочу", "шукаю"}
        keywords = [k for k in keywords if k not in stop_words and len(k) > 2][:5]

        conditions = []
        for keyword in keywords:
            pattern = f"%{keyword}%"
            conditions.extend([
                func.lower(Specialist.name).like(pattern),
                func.lower(Specialist.role).like(pattern),
                func.lower(Specialist.specialty).like(pattern),
            ])

        base = (Specialist.project_id == settings.PROJECT_ID) & (Specialist.is_active == True)
        if conditions:
            query = select(Specialist).where(base, or_(*conditions)).limit(5)
        else:
            query = select(Specialist).where(base).limit(5)

        result = await db.execute(query)
        specialists = result.scalars().all()

        if specialists:
            names = [f"{s.name} ({s.role or s.specialty or 'спеціаліст'})" for s in specialists]
            response_text = (
                "🤖 AI-асистент тимчасово недоступний.\n\n"
                "На основі вашого запиту рекомендую звернутися до:\n"
                + ", ".join(names)
            )
            suggestions = [
                {
                    "id": s.id,
                    "name": s.name,
                    "role": s.role,
                    "specialization": s.specialty,
                }
                for s in specialists
            ]
        else:
            response_text = (
                "🤖 AI-асистент тимчасово недоступний.\n\n"
                "Спробуйте пізніше або перегляньте список спеціалістів через /api/specialists"
            )
            suggestions = []

        return ChatResponse(
            response=response_text,
            is_safe_mode=True,
            model_used=None,
            suggestions=suggestions,
        )
