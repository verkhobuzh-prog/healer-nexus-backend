"""
Learning Engine — batch-аналіз розмов для навчання AI МОЗКУ.
Отримує нові розмови, аналізує через патерни (і опційно Local AI), генерує інсайти.
"""
from __future__ import annotations

import logging
from typing import Any

from app.ai.brain.hybrid_provider import HybridAIProvider

logger = logging.getLogger(__name__)


class LearningEngine:
    """
    Офлайн аналіз розмов: pain points, конверсійні тригери, рекомендації.
    Може використовувати Local AI (Ollama) або лише патерни.
    """

    def __init__(self) -> None:
        self.hybrid = HybridAIProvider()

    async def analyze_batch(
        self,
        conversations: list[Any],
        local_model: str = "llama-3.1-8b",
    ) -> list[dict[str, Any]]:
        """
        Проаналізувати пакет розмов і повернути інсайти.
        local_model — для майбутньої інтеграції з Ollama; поки використовується
        патерн-аналіз через HybridAIProvider.analyze_batch.
        """
        if not conversations:
            logger.info("LearningEngine: немає розмов для аналізу")
            return []

        # Нормалізуємо до списку словників
        payload: list[dict[str, Any]] = []
        for c in conversations:
            if hasattr(c, "messages"):
                payload.append({"messages": c.messages or []})
            elif isinstance(c, dict):
                payload.append(c)
            else:
                payload.append({"messages": []})

        logger.info("LearningEngine: запуск batch-аналізу для %s розмов (local_model=%s)", len(payload), local_model)
        raw = await self.hybrid.analyze_batch(payload)
        insights = [x for x in raw if x]
        logger.info("LearningEngine: отримано інсайтів: %s", len(insights))
        return raw
