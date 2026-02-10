"""
Role Switching Engine — динамічний вибір AI-моделі за контекстом.
Кожна модель має унікальні сильні сторони (емпатія, техніка, гумор тощо).
"""
from __future__ import annotations

import logging
from typing import Any

from app.ai.self_reflection import reflection_engine

logger = logging.getLogger(__name__)


# Профілі моделей (для документації та майбутнього підключення GPT/Claude/DeepSeek)
MODEL_PROFILES = {
    "gemini-1.5-flash": {
        "strengths": ["speed", "multilingual", "general"],
        "use_cases": ["default", "quick_responses"],
    },
    "gpt-4": {
        "strengths": ["empathy", "creativity", "deep_reasoning"],
        "use_cases": ["healing", "coaching", "emotional_support"],
    },
    "grok-2": {
        "strengths": ["humor", "casual", "youthful"],
        "use_cases": ["young_audience", "entertainment"],
    },
    "claude-3-sonnet": {
        "strengths": ["analysis", "structure", "business"],
        "use_cases": ["business_consulting", "legal", "reports"],
    },
    "deepseek-v3": {
        "strengths": ["technical", "math", "coding"],
        "use_cases": ["math_tutoring", "programming", "science"],
    },
}


class RoleSwitcher:
    """
    Динамічний вибір AI-моделі на основі контексту.

    GPT-4: емпатія, креативність (цілителі, коучі).
    Grok: гумор, casual (молода аудиторія).
    Gemini: швидкість, багатомовність (основний).
    Claude: аналіз, структура (бізнес).
    DeepSeek: технічні задачі (вчителі математики).
    """

    async def select_model(
        self,
        message: str,
        user_context: dict[str, Any],
        bot_type: str,
    ) -> str:
        """
        Вибрати оптимальну модель за:
        1) нішею/сервісом (healer → GPT, teacher_math → DeepSeek);
        2) емоційним станом (тривога → GPT);
        3) віком/преміум (преміум → Claude);
        4) за замовчуванням — Gemini.
        """
        # Емоції через існуючий self_reflection
        anxiety_score = reflection_engine.calculate_anxiety_score(message)
        detected_service, _ = reflection_engine.detect_service(message)

        if anxiety_score > 0.7:
            logger.debug("RoleSwitcher: висока тривога → gpt-4 (емпатія)")
            return "gpt-4"

        if user_context.get("service_type") == "teacher_math" or detected_service == "teacher_math":
            logger.debug("RoleSwitcher: математика → deepseek-v3")
            return "deepseek-v3"

        if user_context.get("age", 25) < 20:
            logger.debug("RoleSwitcher: молода аудиторія → grok-2")
            return "grok-2"

        if user_context.get("is_premium"):
            logger.debug("RoleSwitcher: преміум → claude-3-sonnet")
            return "claude-3-sonnet"

        logger.debug("RoleSwitcher: default → gemini-1.5-flash")
        return "gemini-1.5-flash"
