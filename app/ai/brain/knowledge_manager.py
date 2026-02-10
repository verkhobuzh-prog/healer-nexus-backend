"""
Knowledge Manager — управління Knowledge Base інсайтів.
Зберігання та отримання інсайтів з batch-аналізу для покращення стратегій ботів.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeManager:
    """
    Управління базою знань: збереження інсайтів, отримання за service_type.
    Поки in-memory; далі можна перенести на БД (таблиця knowledge_base).
    """

    def __init__(self) -> None:
        self._insights: list[dict[str, Any]] = []
        self._by_service: dict[str, list[dict[str, Any]]] = {}

    async def add_insight(self, insight: dict[str, Any]) -> None:
        """Додати інсайт після batch-аналізу."""
        self._insights.append(insight)
        service = insight.get("service_type") or insight.get("detected_service") or "general"
        if service not in self._by_service:
            self._by_service[service] = []
        self._by_service[service].append(insight)
        logger.debug("KnowledgeManager: додано інсайт для service_type=%s", service)

    def get_insights(self, service_type: str | None = None) -> list[dict[str, Any]]:
        """Повернути інсайти; якщо service_type задано — лише для нього."""
        if service_type is None:
            return list(self._insights)
        return list(self._by_service.get(service_type, []))

    def get_latest(self, limit: int = 50) -> list[dict[str, Any]]:
        """Останні N інсайтів (для адмін-дашборду)."""
        return self._insights[-limit:] if len(self._insights) >= limit else list(self._insights)
