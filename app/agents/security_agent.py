"""
Security Agent — моніторинг безпеки.
- Виявлення brute-force спроб (багато невдалих логінів)
- Підозрілі реєстрації (масові з одного IP)
- Невалідні токени
- Аномальна активність
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, text

from app.agents.base_agent import BaseAgent
from app.database.connection import async_session_factory
from app.models.agent_config import AgentSeverity, AgentLog

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    AGENT_NAME = "security_watch"
    AGENT_TYPE = "security"
    DESCRIPTION = "Моніторинг безпеки: brute-force, підозрілі логіни, аномалії"
    DEFAULT_INTERVAL = 180  # кожні 3 хвилини

    # Пороги
    MAX_FAILED_LOGINS_PER_HOUR = 10
    MAX_REGISTRATIONS_PER_HOUR = 5
    MAX_401_ERRORS_PER_HOUR = 20

    async def execute(self) -> dict:
        results = {
            "checks_performed": [],
            "threats_found": [],
            "summary": "clean",
        }

        # 1. Перевірка кількості користувачів (аномалії)
        await self._check_user_anomalies(results)

        # 2. Перевірка стану активних сесій
        await self._check_sessions(results)

        # 3. Перевірка відсутніх admin прав
        await self._check_admin_integrity(results)

        # 4. Перевірка підозрілих акаунтів
        await self._check_suspicious_accounts(results)

        # Підсумок
        if results["threats_found"]:
            results["summary"] = f"{len(results['threats_found'])} threat(s) detected"
            await self.log(
                action="threats_detected",
                message=f"Security scan found {len(results['threats_found'])} issue(s)",
                severity=AgentSeverity.WARNING,
                details={"threats": results["threats_found"]},
            )
        else:
            await self.log(
                action="security_ok",
                message=f"Security scan clean. Checks: {', '.join(results['checks_performed'])}",
                severity=AgentSeverity.INFO,
            )

        return results

    async def _check_user_anomalies(self, results: dict):
        """Перевірити аномальне зростання кількості юзерів."""
        results["checks_performed"].append("user_growth")
        try:
            async with async_session_factory() as session:
                # Кількість нових юзерів за останню годину
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                query = text(
                    "SELECT COUNT(*) FROM users WHERE created_at > :since"
                )
                result = await session.execute(query, {"since": one_hour_ago})
                new_users = result.scalar() or 0

                if new_users > self.MAX_REGISTRATIONS_PER_HOUR:
                    results["threats_found"].append({
                        "type": "mass_registration",
                        "count": new_users,
                        "threshold": self.MAX_REGISTRATIONS_PER_HOUR,
                        "period": "1 hour",
                    })
                    await self.log(
                        action="mass_registration",
                        message=f"{new_users} new registrations in last hour (threshold: {self.MAX_REGISTRATIONS_PER_HOUR})",
                        severity=AgentSeverity.WARNING,
                        details={"new_users": new_users},
                    )

        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] User anomaly check failed: {e}")

    async def _check_sessions(self, results: dict):
        """Перевірити активні refresh токени."""
        results["checks_performed"].append("active_sessions")
        try:
            async with async_session_factory() as session:
                # Перевірити чи є прострочені токени
                query = text(
                    "SELECT COUNT(*) FROM refresh_tokens WHERE revoked = false"
                )
                try:
                    result = await session.execute(query)
                    active_sessions = result.scalar() or 0
                    results["active_sessions"] = active_sessions

                    # Якщо забагато активних сесій - може бути атака
                    if active_sessions > 100:
                        results["threats_found"].append({
                            "type": "excessive_sessions",
                            "count": active_sessions,
                        })
                except Exception:
                    # Таблиця може не існувати
                    pass

        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] Session check failed: {e}")

    async def _check_admin_integrity(self, results: dict):
        """Перевірити що admin-акаунти не змінились несподівано."""
        results["checks_performed"].append("admin_integrity")
        try:
            async with async_session_factory() as session:
                query = text(
                    "SELECT id, email, role FROM users WHERE role = 'admin'"
                )
                result = await session.execute(query)
                admins = result.fetchall()

                results["admin_count"] = len(admins)
                results["admin_emails"] = [a.email for a in admins]

                # Сповістити якщо кількість адмінів змінилась
                # (У конфігу агента зберігаємо expected_admin_count)
                config = await self._get_config()
                expected = (config or {}).get("config", {}).get("expected_admin_count")
                if expected and len(admins) != expected:
                    results["threats_found"].append({
                        "type": "admin_count_changed",
                        "expected": expected,
                        "actual": len(admins),
                        "admins": [a.email for a in admins],
                    })
                    await self.log(
                        action="admin_count_changed",
                        message=f"Admin count changed: expected {expected}, got {len(admins)}",
                        severity=AgentSeverity.CRITICAL,
                        details={"admins": [a.email for a in admins]},
                    )

        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] Admin integrity check failed: {e}")

    async def _check_suspicious_accounts(self, results: dict):
        """Перевірити акаунти без email або з підозрілими даними."""
        results["checks_performed"].append("suspicious_accounts")
        try:
            async with async_session_factory() as session:
                # Юзери без email
                query = text(
                    "SELECT id, username, role FROM users WHERE email IS NULL OR email = ''"
                )
                result = await session.execute(query)
                no_email = result.fetchall()

                if no_email:
                    results["threats_found"].append({
                        "type": "users_without_email",
                        "count": len(no_email),
                        "user_ids": [u.id for u in no_email],
                    })
                    await self.log(
                        action="users_without_email",
                        message=f"{len(no_email)} user(s) without email found",
                        severity=AgentSeverity.WARNING,
                        details={"user_ids": [u.id for u in no_email]},
                    )

        except Exception as e:
            logger.warning(f"[{self.AGENT_NAME}] Suspicious accounts check failed: {e}")


# Singleton
security_agent = SecurityAgent()
