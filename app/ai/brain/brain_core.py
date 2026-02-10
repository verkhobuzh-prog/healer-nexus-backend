"""
Центральний AI МОЗОК платформи Healer Nexus.
Координує AI-агентів, зберігає розмови, запускає batch-навчання та оновлення стратегій.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.conversation import Conversation
from app.ai.brain.role_switcher import RoleSwitcher
from app.ai.brain.hybrid_provider import HybridAIProvider
from app.ai.brain.knowledge_manager import KnowledgeManager
from app.ai.brain.learning_engine import LearningEngine

logger = logging.getLogger(__name__)


class AIBrainCore:
    """
    Головний координатор AI платформи.

    Функції:
    - Вибір моделі (role switching).
    - Аналіз розмов (batch learning).
    - Оновлення стратегій (промпти, логіка ботів).
    - Моніторинг метрик (churn, conversion, engagement).
    """

    def __init__(self) -> None:
        self.hybrid_provider = HybridAIProvider()
        self.role_switcher = RoleSwitcher()
        self.knowledge_manager = KnowledgeManager()
        self.learning_engine = LearningEngine()

    async def process_user_message(
        self,
        message: str,
        context: dict[str, Any],
        bot_type: str,
    ) -> dict[str, Any]:
        """
        Обробка повідомлення від користувача (реальний час).

        1. Вибір оптимальної моделі (role switching).
        2. Генерація відповіді (Gemini live).
        3. Збереження розмови для подальшого batch-аналізу (якщо передано db).
        """
        optimal_model = await self.role_switcher.select_model(
            message=message,
            user_context=context,
            bot_type=bot_type,
        )
        response = await self.hybrid_provider.generate_live(
            message=message,
            model=optimal_model,
            context=context,
        )
        if context.get("db") and context.get("user_id") is not None:
            await self._save_conversation(message, response, context, bot_type)
        return response

    async def _save_conversation(
        self,
        user_message: str,
        response: dict[str, Any],
        context: dict[str, Any],
        bot_type: str,
    ) -> None:
        """Зберегти розмову в БД для подальшого batch-аналізу."""
        db: AsyncSession | None = context.get("db")
        if not db:
            return
        user_id = context.get("user_id")
        if user_id is None:
            return
        try:
            text = response.get("text", "") if isinstance(response, dict) else str(response)
            messages = [
                {"role": "user", "text": user_message},
                {"role": "assistant", "text": text},
            ]
            conv = Conversation(
                project_id=getattr(settings, "PROJECT_ID", "healer_nexus"),
                user_id=user_id,
                bot_type=bot_type,
                messages=messages,
                message_count=len(messages),
                converted=context.get("converted", False),
                pain_points=[],
                detected_emotions={},
                ai_insights={},
            )
            db.add(conv)
            await db.commit()
            logger.debug("BrainCore: збережено розмову user_id=%s, bot_type=%s", user_id, bot_type)
        except Exception as e:
            logger.error("BrainCore: помилка збереження розмови: %s", e, exc_info=True)
            await db.rollback()

    async def run_batch_learning(self, db: AsyncSession) -> None:
        """
        Офлайн аналіз розмов (раз на день).

        1. Отримати нові розмови (ще не проаналізовані).
        2. Аналіз через LearningEngine (патерни / Local AI).
        3. Оновити KnowledgeManager.
        4. Записати ai_insights у Conversation та опційно event_bus для стратегій.
        """
        new_conversations = await self._get_unanalyzed_conversations(db)
        logger.info("BrainCore: batch learning — розмов для аналізу: %s", len(new_conversations))

        if not new_conversations:
            return

        insights = await self.learning_engine.analyze_batch(
            new_conversations,
            local_model="llama-3.1-8b",
        )

        for insight in insights:
            if insight is not None:
                await self.knowledge_manager.add_insight(insight)

        for conv, insight in zip(new_conversations, insights):
            if insight is not None:
                try:
                    conv.ai_insights = insight
                    db.add(conv)
                except Exception as e:
                    logger.warning("BrainCore: не вдалося оновити ai_insights: %s", e)
        await db.commit()

        await self._update_bot_strategies([x for x in insights if x is not None])
        logger.info("BrainCore: learning complete, інсайтів: %s", len(insights))

    async def _get_unanalyzed_conversations(self, db: AsyncSession) -> list[Conversation]:
        """Отримати розмови без заповненого ai_insights."""
        result = await db.execute(
            select(Conversation).where(
                Conversation.project_id == getattr(settings, "PROJECT_ID", "healer_nexus"),
                Conversation.deleted_at.is_(None),
                Conversation.ai_insights == {},
            ).order_by(Conversation.id.desc()).limit(500)
        )
        return list(result.scalars().all())

    async def _update_bot_strategies(self, insights: list[dict[str, Any]]) -> None:
        """
        Оновити логіку ботів на основі інсайтів.
        Опційно: надіслати подію в event_bus для consumer/specialist ботів.
        """
        for insight in insights:
            if insight.get("type") == "conversion_pattern":
                recommendation = insight.get("recommendation")
                if recommendation:
                    logger.info("BrainCore: рекомендація для ботів: %s", recommendation)
                try:
                    from app.core.event_bus import get_event_bus
                    bus = await get_event_bus(getattr(settings, "PROJECT_ID", "healer_nexus"))
                    if hasattr(bus, "emit"):
                        await bus.emit("bot.update_strategy", {"bot": "consumer", "strategy": recommendation})
                except Exception as e:
                    logger.debug("BrainCore: event_bus недоступний (норма для stub): %s", e)
