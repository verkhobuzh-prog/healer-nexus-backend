"""
HealthCheck Agent — моніторинг здоров'я системи.
- Перевіряє /api/health endpoint
- Перевіряє з'єднання з БД
- Моніторить час відповіді
- Сповіщає якщо щось впало
"""
from __future__ import annotations

import logging
import time

import httpx
from sqlalchemy import text

from app.agents.base_agent import BaseAgent
from app.database.connection import async_session_factory
from app.models.agent_config import AgentSeverity

logger = logging.getLogger(__name__)


class HealthCheckAgent(BaseAgent):
    AGENT_NAME = "health_check"
    AGENT_TYPE = "health_check"
    DESCRIPTION = "Моніторинг здоров'я API, БД та часу відповіді"
    DEFAULT_INTERVAL = 120  # кожні 2 хвилини

    async def execute(self) -> dict:
        results = {
            "api_health": None,
            "db_connection": None,
            "response_time_ms": None,
            "issues": [],
        }

        # 1. Перевірка API health
        try:
            from app.config import settings
            base_url = getattr(settings, "BASE_URL", "http://localhost:8000")

            start = time.time()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{base_url}/api/health")
                response_time = int((time.time() - start) * 1000)

            results["response_time_ms"] = response_time

            if resp.status_code == 200:
                results["api_health"] = "ok"

                # Попередження якщо відповідь повільна
                if response_time > 3000:
                    results["issues"].append(f"Slow response: {response_time}ms")
                    await self.log(
                        action="slow_response",
                        message=f"API health response time: {response_time}ms (threshold: 3000ms)",
                        severity=AgentSeverity.WARNING,
                        details={"response_time_ms": response_time},
                    )
            else:
                results["api_health"] = f"error_{resp.status_code}"
                results["issues"].append(f"Health endpoint returned {resp.status_code}")
                await self.log(
                    action="api_health_fail",
                    message=f"API /health returned HTTP {resp.status_code}",
                    severity=AgentSeverity.ERROR,
                    success=False,
                    details={"status_code": resp.status_code, "body": resp.text[:500]},
                )

        except httpx.ConnectError:
            results["api_health"] = "unreachable"
            results["issues"].append("API unreachable")
            await self.log(
                action="api_unreachable",
                message="Cannot connect to API — service might be down",
                severity=AgentSeverity.CRITICAL,
                success=False,
            )
        except Exception as e:
            results["api_health"] = "error"
            results["issues"].append(str(e))
            await self.log(
                action="health_check_error",
                message=f"Health check error: {str(e)}",
                severity=AgentSeverity.ERROR,
                success=False,
            )

        # 2. Перевірка БД
        try:
            start = time.time()
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
                db_time = int((time.time() - start) * 1000)

            results["db_connection"] = "ok"
            results["db_response_ms"] = db_time

            if db_time > 2000:
                results["issues"].append(f"DB slow: {db_time}ms")
                await self.log(
                    action="db_slow",
                    message=f"Database response time: {db_time}ms",
                    severity=AgentSeverity.WARNING,
                    details={"db_response_ms": db_time},
                )

        except Exception as e:
            results["db_connection"] = "error"
            results["issues"].append(f"DB error: {str(e)}")
            await self.log(
                action="db_connection_fail",
                message=f"Database connection failed: {str(e)}",
                severity=AgentSeverity.CRITICAL,
                success=False,
                details={"error": str(e)},
            )

        # 3. Підсумковий лог (тільки якщо все ОК)
        if not results["issues"]:
            await self.log(
                action="health_ok",
                message=f"All systems OK (API: {results['response_time_ms']}ms, DB: {results.get('db_response_ms', '?')}ms)",
                severity=AgentSeverity.INFO,
                duration_ms=results.get("response_time_ms"),
            )

        return results


# Singleton
health_check_agent = HealthCheckAgent()
