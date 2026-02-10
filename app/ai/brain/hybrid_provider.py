"""
Hybrid AI Provider — Gemini (live) + Local AI (batch).
Об'єднує реальночасовий чат із користувачами та офлайн batch-аналіз розмов.
"""
from __future__ import annotations

import logging
from typing import Any

from app.ai.providers import get_ai_provider

logger = logging.getLogger(__name__)


class HybridAIProvider:
    """
    Об'єднує два типи AI:
    - Gemini: реальний час (чат з користувачами).
    - Local AI: офлайн аналіз (batch learning; опційно через Ollama).
    """

    def __init__(self) -> None:
        self._gemini = None  # lazy init

    def _get_gemini(self):
        """Лінива ініціалізація Gemini-провайдера."""
        if self._gemini is None:
            self._gemini = get_ai_provider()
        return self._gemini

    async def generate_live(
        self,
        message: str,
        model: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Генерація відповіді в реальному часі.
        Зараз усі моделі обслуговуються через Gemini (fallback).
        """
        # Підтримка інших моделей — майбутнє; поки лише Gemini
        supported_live = ["gemini-1.5-flash", "gpt-4", "grok-2", "claude-3-sonnet", "deepseek-v3"]
        if model not in supported_live:
            logger.warning("HybridProvider: модель %s недоступна, fallback на Gemini", model)
            model = "gemini-1.5-flash"

        try:
            provider = self._get_gemini()
            history = context.get("history", [])
            role = context.get("role", "default")
            db = context.get("db")
            result = await provider.generate_response(
                message=message,
                history=history,
                role=role,
                user_id=context.get("user_id", 0),
                db=db,
            )
            # Уніфікований формат: текст + метадані
            text = result.get("text", "") if isinstance(result, dict) else str(result)
            return {"text": text, "metadata": result.get("metadata", {}) if isinstance(result, dict) else {}}
        except Exception as e:
            logger.error("HybridProvider: помилка live-генерації: %s", e, exc_info=True)
            return await self._fallback_generate(message, context)

    async def _fallback_generate(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        """Fallback: безпечна відповідь при збої AI."""
        return {
            "text": "Зараз не можу відповісти. Спробуйте пізніше або перегляньте спеціалістів: /api/specialists",
            "metadata": {"fallback": True},
        }

    async def analyze_batch(self, conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Офлайн аналіз розмов (batch).
        Аналізує pain points, успішні фрази, причини churn, conversion triggers.
        За відсутності Local AI повертає базові інсайти з ключових слів.
        """
        insights: list[dict[str, Any] | None] = []
        for conv in conversations:
            try:
                analysis = await self._analyze_one_conversation(conv)
                insights.append(analysis)
            except Exception as e:
                logger.error("HybridProvider: помилка batch-аналізу розмови: %s", e)
                insights.append(None)
        logger.info("HybridProvider: batch-аналіз завершено, інсайтів: %s", sum(1 for x in insights if x))
        return insights

    async def _analyze_one_conversation(self, conv: dict[str, Any]) -> dict[str, Any] | None:
        """Один прохід аналізу розмови (без Local AI — прості патерни)."""
        messages = conv.get("messages") or []
        if not messages:
            return None
        texts = []
        for m in messages:
            t = m.get("text") or m.get("content") or ""
            if isinstance(t, str):
                texts.append(t)
        full_text = " ".join(texts).lower()
        # Прості тригери для конверсії
        conversion_triggers = []
        if "записати" in full_text or "запис" in full_text:
            conversion_triggers.append("згадка запису")
        if "ціна" in full_text or "скільки" in full_text:
            conversion_triggers.append("ціновий інтерес")
        pain_candidates = []
        for w in ("тривога", "стрес", "медитація", "коуч", "вчитель", "дизайн"):
            if w in full_text:
                pain_candidates.append(w)
        return {
            "type": "conversion_pattern",
            "conversion_triggers": conversion_triggers,
            "pain_points": pain_candidates,
            "message_count": len(messages),
            "recommendation": "Підсилити CTA після згадки ціни або запису.",
        }
