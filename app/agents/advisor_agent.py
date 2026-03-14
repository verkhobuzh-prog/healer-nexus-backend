"""
Advisor Agent — AI-powered рекомендації через Gemini.
- Аналізує метрики платформи
- Дає рекомендації по покращенню
- Шукає паттерни в даних
- Генерує щоденний звіт
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.agents.base_agent import BaseAgent
from app.database.connection import async_session_factory
from app.models.agent_config import AgentSeverity

logger = logging.getLogger(__name__)


class AdvisorAgent(BaseAgent):
    AGENT_NAME = "advisor"
    AGENT_TYPE = "advisor"
    DESCRIPTION = "AI рекомендації по покращенню платформи (Gemini)"
    DEFAULT_INTERVAL = 86400  # раз на добу (24 години)

    async def execute(self) -> dict:
        results = {
            "metrics": {},
            "recommendations": [],
            "ai_analysis": None,
        }

        # 1. Зібрати метрики
        metrics = await self._collect_metrics()
        results["metrics"] = metrics

        # 2. Базові рекомендації (без AI)
        recommendations = self._generate_basic_recommendations(metrics)
        results["recommendations"] = recommendations

        # 3. AI аналіз через Gemini (якщо доступний)
        try:
            from app.config import settings
            if settings.GEMINI_ENABLED:
                ai_analysis = await self._gemini_analyze(metrics)
                results["ai_analysis"] = ai_analysis
        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] Gemini analysis skipped: {e}")

        # Лог
        severity = AgentSeverity.INFO
        if any(r.get("priority") == "high" for r in recommendations):
            severity = AgentSeverity.WARNING

        await self.log(
            action="daily_report",
            message=self._format_report(metrics, recommendations),
            severity=severity,
            details=results,
        )

        return results

    async def _collect_metrics(self) -> dict:
        """Зібрати метрики з БД."""
        metrics = {}
        try:
            async with async_session_factory() as session:
                # Загальна кількість
                for table, key in [
                    ("users", "total_users"),
                    ("specialists", "total_specialists"),
                    ("bookings", "total_bookings"),
                    ("blog_posts", "total_posts"),
                    ("messages", "total_messages"),
                ]:
                    try:
                        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        metrics[key] = result.scalar() or 0
                    except Exception:
                        metrics[key] = "N/A"

                # Активні юзери (з role)
                try:
                    result = await session.execute(text(
                        "SELECT role, COUNT(*) as cnt FROM users GROUP BY role"
                    ))
                    metrics["users_by_role"] = {row.role: row.cnt for row in result.fetchall()}
                except Exception:
                    metrics["users_by_role"] = {}

                # Букінги по статусу
                try:
                    result = await session.execute(text(
                        "SELECT status, COUNT(*) as cnt FROM bookings GROUP BY status"
                    ))
                    metrics["bookings_by_status"] = {row.status: row.cnt for row in result.fetchall()}
                except Exception:
                    metrics["bookings_by_status"] = {}

                # Пости по статусу
                try:
                    result = await session.execute(text(
                        "SELECT status, COUNT(*) as cnt FROM blog_posts GROUP BY status"
                    ))
                    metrics["posts_by_status"] = {row.status: row.cnt for row in result.fetchall()}
                except Exception:
                    metrics["posts_by_status"] = {}

                # Верифіковані спеціалісти
                try:
                    result = await session.execute(text(
                        "SELECT COUNT(*) FROM specialists WHERE is_verified = true"
                    ))
                    metrics["verified_specialists"] = result.scalar() or 0
                except Exception:
                    metrics["verified_specialists"] = "N/A"

        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Metrics collection failed: {e}")

        return metrics

    def _generate_basic_recommendations(self, metrics: dict) -> list:
        """Генерувати рекомендації на основі метрик."""
        recs = []

        # 1. Мало спеціалістів
        total_specs = metrics.get("total_specialists", 0)
        if isinstance(total_specs, int) and total_specs < 10:
            recs.append({
                "priority": "high",
                "category": "growth",
                "title": "Потрібно більше спеціалістів",
                "description": f"Зараз {total_specs} спеціаліст(ів). Для маркетплейсу потрібно мінімум 10-20.",
                "action": "Запустити рекламну кампанію для залучення спеціалістів",
            })

        # 2. Мало опублікованих постів
        posts_by_status = metrics.get("posts_by_status", {})
        published = posts_by_status.get("published", 0)
        if isinstance(published, int) and published < 5:
            recs.append({
                "priority": "medium",
                "category": "content",
                "title": "Мало контенту",
                "description": f"Лише {published} опублікованих пост(ів). SEO потребує контенту.",
                "action": "Увімкнути AI Blog Generator або попросити спеціалістів писати",
            })

        # 3. Багато pending букінгів
        bookings_status = metrics.get("bookings_by_status", {})
        pending = bookings_status.get("pending", 0)
        if isinstance(pending, int) and pending > 5:
            recs.append({
                "priority": "high",
                "category": "operations",
                "title": f"{pending} необроблених бронювань",
                "description": "Pending букінги шкодять конверсії. Клієнти чекають відповіді.",
                "action": "Нагадати спеціалістам обробити бронювання",
            })

        # 4. Мало верифікованих спеціалістів
        verified = metrics.get("verified_specialists", 0)
        if isinstance(verified, int) and isinstance(total_specs, int):
            if total_specs > 0 and verified / total_specs < 0.5:
                recs.append({
                    "priority": "medium",
                    "category": "trust",
                    "title": "Верифікувати спеціалістів",
                    "description": f"Лише {verified} з {total_specs} верифіковані. Це впливає на довіру.",
                    "action": "Перевірити і верифікувати активних спеціалістів",
                })

        return recs

    async def _gemini_analyze(self, metrics: dict) -> str | None:
        """Аналіз метрик через Gemini AI."""
        try:
            from google import genai

            from app.config import settings
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            prompt = (
                "Ти AI-аналітик маркетплейсу Healer Nexus (платформа для цілителів, коучів, дизайнерів). "
                "Проаналізуй метрики та дай 3-5 конкретних рекомендацій українською. "
                "Будь коротким (до 200 слів).\n\n"
                f"Метрики:\n{metrics}"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            return response.text

        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] Gemini analysis failed: {e}")
            return None

    def _format_report(self, metrics: dict, recommendations: list) -> str:
        """Форматований звіт для Telegram."""
        lines = ["📊 Щоденний звіт Healer Nexus\n"]

        # Метрики
        lines.append(f"👥 Юзерів: {metrics.get('total_users', '?')}")
        lines.append(f"🧑‍⚕️ Спеціалістів: {metrics.get('total_specialists', '?')}")
        lines.append(f"📝 Постів: {metrics.get('total_posts', '?')}")
        lines.append(f"📅 Букінгів: {metrics.get('total_bookings', '?')}")
        lines.append(f"💬 Повідомлень: {metrics.get('total_messages', '?')}")

        # Рекомендації
        if recommendations:
            lines.append(f"\n⚡ Рекомендації ({len(recommendations)}):")
            for r in recommendations[:3]:
                emoji = "🔴" if r["priority"] == "high" else "🟡"
                lines.append(f"{emoji} {r['title']}")

        return "\n".join(lines)


# Singleton
advisor_agent = AdvisorAgent()
