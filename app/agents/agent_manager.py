"""
Agent Manager — оркестратор усіх AI-агентів.
- Запуск/зупинка всіх агентів
- Статус кожного агента
- Ручний запуск
- Інтеграція з startup/shutdown FastAPI
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.agents.base_agent import BaseAgent
from app.agents.health_check_agent import health_check_agent
from app.agents.security_agent import security_agent
from app.agents.bug_scanner_agent import bug_scanner_agent
from app.agents.qa_tester_agent import qa_tester_agent
from app.agents.advisor_agent import advisor_agent
from app.database.connection import async_session_factory
from app.models.agent_config import AgentConfig, AgentStatus, AgentLog

logger = logging.getLogger(__name__)


class AgentManager:
    """Центральний менеджер AI-агентів."""

    def __init__(self):
        # Реєстр агентів
        self._agents: dict[str, BaseAgent] = {
            "health_check": health_check_agent,
            "security_watch": security_agent,
            "bug_scanner": bug_scanner_agent,
            "qa_tester": qa_tester_agent,
            "advisor": advisor_agent,
        }

    @property
    def agents(self) -> dict[str, BaseAgent]:
        return self._agents

    # ─── Lifecycle ────────────────────────────────────────

    async def start_all(self):
        """Запустити всіх агентів (викликається при startup FastAPI)."""
        logger.info("🤖 Agent Manager: starting all agents...")
        for name, agent in self._agents.items():
            try:
                await agent.start()
                logger.info(f"  ✅ {name} — started (will check config in loop)")
            except Exception as e:
                logger.error(f"  ❌ {name} — failed to start: {e}")

        logger.info(f"🤖 Agent Manager: {len(self._agents)} agents initialized")

    async def stop_all(self):
        """Зупинити всіх агентів (викликається при shutdown FastAPI)."""
        logger.info("🤖 Agent Manager: stopping all agents...")
        for name, agent in self._agents.items():
            try:
                await agent.stop()
            except Exception as e:
                logger.error(f"  ❌ {name} — failed to stop: {e}")
        logger.info("🤖 Agent Manager: all agents stopped")

    # ─── Individual Control ───────────────────────────────

    async def start_agent(self, agent_name: str) -> dict:
        """Запустити конкретного агента."""
        agent = self._agents.get(agent_name)
        if not agent:
            return {"error": f"Agent '{agent_name}' not found"}

        await agent.start()
        return {"agent": agent_name, "status": "started"}

    async def stop_agent(self, agent_name: str) -> dict:
        """Зупинити конкретного агента."""
        agent = self._agents.get(agent_name)
        if not agent:
            return {"error": f"Agent '{agent_name}' not found"}

        await agent.stop()
        return {"agent": agent_name, "status": "stopped"}

    async def run_agent_once(self, agent_name: str) -> dict:
        """Ручний одноразовий запуск агента."""
        agent = self._agents.get(agent_name)
        if not agent:
            return {"error": f"Agent '{agent_name}' not found"}

        return await agent.run_once()

    # ─── Enable/Disable via DB ────────────────────────────

    async def enable_agent(self, agent_name: str) -> dict:
        """Увімкнути агента (через БД конфіг)."""
        try:
            async with async_session_factory() as session:
                await session.execute(
                    update(AgentConfig)
                    .where(AgentConfig.agent_name == agent_name)
                    .values(is_enabled=True, status=AgentStatus.ACTIVE)
                )
                await session.commit()
            return {"agent": agent_name, "enabled": True}
        except Exception as e:
            return {"error": str(e)}

    async def disable_agent(self, agent_name: str) -> dict:
        """Вимкнути агента (через БД конфіг)."""
        try:
            async with async_session_factory() as session:
                await session.execute(
                    update(AgentConfig)
                    .where(AgentConfig.agent_name == agent_name)
                    .values(is_enabled=False, status=AgentStatus.PAUSED)
                )
                await session.commit()
            return {"agent": agent_name, "enabled": False}
        except Exception as e:
            return {"error": str(e)}

    # ─── Status ───────────────────────────────────────────

    async def get_status(self) -> dict:
        """Статус усіх агентів."""
        status = {}
        try:
            async with async_session_factory() as session:
                result = await session.execute(select(AgentConfig))
                configs = result.scalars().all()

                for config in configs:
                    agent = self._agents.get(config.agent_name)
                    status[config.agent_name] = {
                        "type": config.agent_type,
                        "description": config.description,
                        "status": config.status.value if config.status else "unknown",
                        "is_enabled": config.is_enabled,
                        "is_running": agent.is_running if agent else False,
                        "interval_seconds": config.interval_seconds,
                        "last_run_at": config.last_run_at.isoformat() if config.last_run_at else None,
                        "total_runs": config.total_runs,
                        "total_issues_found": config.total_issues_found,
                        "notify_telegram": config.notify_telegram,
                    }

        except Exception as e:
            logger.error(f"Agent Manager: failed to get status: {e}")
            # Fallback — показати з пам'яті
            for name, agent in self._agents.items():
                status[name] = {
                    "type": agent.AGENT_TYPE,
                    "description": agent.DESCRIPTION,
                    "is_running": agent.is_running,
                    "is_enabled": "unknown (db error)",
                }

        return status

    async def get_logs(
        self,
        agent_name: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list:
        """Отримати логи агентів."""
        try:
            async with async_session_factory() as session:
                query = select(AgentLog).order_by(AgentLog.created_at.desc()).limit(limit)

                if agent_name:
                    query = query.where(AgentLog.agent_name == agent_name)
                if severity:
                    query = query.where(AgentLog.severity == severity)

                result = await session.execute(query)
                logs = result.scalars().all()

                return [
                    {
                        "id": log.id,
                        "agent_name": log.agent_name,
                        "severity": log.severity.value if log.severity else "info",
                        "action": log.action,
                        "message": log.message,
                        "success": log.success,
                        "duration_ms": log.duration_ms,
                        "telegram_sent": log.telegram_sent,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                        "details": log.details,
                    }
                    for log in logs
                ]
        except Exception as e:
            logger.error(f"Agent Manager: failed to get logs: {e}")
            return []

    async def update_config(self, agent_name: str, updates: dict) -> dict:
        """Оновити конфігурацію агента."""
        try:
            allowed_fields = {
                "interval_seconds", "notify_telegram",
                "notify_on_severity", "config",
            }
            safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}

            if not safe_updates:
                return {"error": "No valid fields to update"}

            async with async_session_factory() as session:
                await session.execute(
                    update(AgentConfig)
                    .where(AgentConfig.agent_name == agent_name)
                    .values(**safe_updates)
                )
                await session.commit()

            return {"agent": agent_name, "updated": list(safe_updates.keys())}
        except Exception as e:
            return {"error": str(e)}


# Singleton
agent_manager = AgentManager()
