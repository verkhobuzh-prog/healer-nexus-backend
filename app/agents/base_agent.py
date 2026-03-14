"""
Base Agent — базовий клас для всіх AI-агентів Healer Nexus.
Кожен агент:
- Працює як фоновий asyncio task
- Логує дії в agent_logs
- Сповіщає в Telegram при проблемах
- Контролюється через agent_configs (увімкнути/вимкнути/пауза)
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session_factory
from app.models.agent_config import AgentConfig, AgentLog, AgentStatus, AgentSeverity

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Базовий клас AI-агента."""

    # Перевизначити в дочірніх класах
    AGENT_NAME: str = "base_agent"
    AGENT_TYPE: str = "base"
    DESCRIPTION: str = "Base agent"
    DEFAULT_INTERVAL: int = 300  # секунд

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._telegram_notifier = None

    # ─── Lifecycle ────────────────────────────────────────

    async def start(self):
        """Запустити агента як фоновий таск."""
        if self._running:
            logger.warning(f"[{self.AGENT_NAME}] Already running")
            return

        # Переконатись що конфіг існує в БД
        await self._ensure_config()

        self._running = True
        self._task = asyncio.create_task(self._loop(), name=f"agent_{self.AGENT_NAME}")
        logger.info(f"[{self.AGENT_NAME}] Started")

    async def stop(self):
        """Зупинити агента."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info(f"[{self.AGENT_NAME}] Stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ─── Main Loop ────────────────────────────────────────

    async def _loop(self):
        """Основний цикл агента."""
        while self._running:
            try:
                config = await self._get_config()

                # Перевірити чи агент увімкнений
                if not config or not config.get("is_enabled"):
                    await asyncio.sleep(30)  # Перевіряти кожні 30 сек чи увімкнули
                    continue

                interval = config.get("interval_seconds", self.DEFAULT_INTERVAL)

                # Запустити виконання
                start_time = time.time()
                try:
                    await self.execute()
                    duration_ms = int((time.time() - start_time) * 1000)

                    # Оновити статистику
                    await self._update_run_stats(duration_ms)

                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    await self.log(
                        action="execute_error",
                        message=f"Agent execution failed: {str(e)}",
                        severity=AgentSeverity.ERROR,
                        success=False,
                        duration_ms=duration_ms,
                        details={"error": str(e), "type": type(e).__name__},
                    )
                    logger.exception(f"[{self.AGENT_NAME}] Execution error")

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[{self.AGENT_NAME}] Loop error: {e}")
                await asyncio.sleep(60)

    # ─── Abstract ─────────────────────────────────────────

    @abstractmethod
    async def execute(self):
        """Основна логіка агента. Перевизначити в дочірньому класі."""
        pass

    # ─── Logging ──────────────────────────────────────────

    async def log(
        self,
        action: str,
        message: str,
        severity: AgentSeverity = AgentSeverity.INFO,
        success: bool = True,
        duration_ms: int | None = None,
        details: dict | None = None,
    ):
        """Записати лог дії агента в БД + Telegram якщо потрібно."""
        try:
            async with async_session_factory() as session:
                log_entry = AgentLog(
                    agent_name=self.AGENT_NAME,
                    severity=severity,
                    action=action,
                    message=message,
                    details=details,
                    success=success,
                    duration_ms=duration_ms,
                )
                session.add(log_entry)

                # Перевірити чи потрібно сповістити Telegram
                config = await self._get_config_from_session(session)
                should_notify = False
                if config and config.notify_telegram:
                    severity_levels = {
                        "info": 0, "warning": 1, "error": 2, "critical": 3
                    }
                    min_level = severity_levels.get(config.notify_on_severity, 1)
                    current_level = severity_levels.get(severity.value, 0)
                    should_notify = current_level >= min_level

                if should_notify:
                    await self._send_telegram(severity, action, message, details)
                    log_entry.telegram_sent = True

                await session.commit()

        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Failed to write log: {e}")

    # ─── Telegram ─────────────────────────────────────────

    async def _send_telegram(
        self,
        severity: AgentSeverity,
        action: str,
        message: str,
        details: dict | None = None,
    ):
        """Відправити сповіщення в Telegram."""
        try:
            from app.config import settings

            bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
            admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)

            if not bot_token or not admin_chat_id:
                logger.debug(f"[{self.AGENT_NAME}] Telegram not configured, skipping notification")
                return

            import httpx

            severity_emoji = {
                AgentSeverity.INFO: "ℹ️",
                AgentSeverity.WARNING: "⚠️",
                AgentSeverity.ERROR: "🔴",
                AgentSeverity.CRITICAL: "🚨",
            }
            emoji = severity_emoji.get(severity, "📋")

            text = (
                f"{emoji} <b>Agent: {self.AGENT_NAME}</b>\n"
                f"<b>Severity:</b> {severity.value.upper()}\n"
                f"<b>Action:</b> {action}\n"
                f"<b>Message:</b> {message}\n"
            )
            if details:
                # Лімітувати деталі до 500 символів
                details_str = str(details)[:500]
                text += f"\n<b>Details:</b>\n<code>{details_str}</code>"

            text += f"\n\n🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"

            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": admin_chat_id,
                        "text": text[:4000],  # Telegram limit
                        "parse_mode": "HTML",
                    },
                )

        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Telegram send failed: {e}")

    # ─── Config Management ────────────────────────────────

    async def _ensure_config(self):
        """Створити конфіг агента в БД якщо не існує."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(AgentConfig).where(AgentConfig.agent_name == self.AGENT_NAME)
                )
                config = result.scalar_one_or_none()

                if not config:
                    config = AgentConfig(
                        agent_name=self.AGENT_NAME,
                        agent_type=self.AGENT_TYPE,
                        description=self.DESCRIPTION,
                        status=AgentStatus.PAUSED,
                        is_enabled=False,
                        interval_seconds=self.DEFAULT_INTERVAL,
                        notify_telegram=True,
                        notify_on_severity="warning",
                    )
                    session.add(config)
                    await session.commit()
                    logger.info(f"[{self.AGENT_NAME}] Config created in DB")

        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Failed to ensure config: {e}")

    async def _get_config(self) -> dict | None:
        """Отримати конфіг агента з БД."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(AgentConfig).where(AgentConfig.agent_name == self.AGENT_NAME)
                )
                config = result.scalar_one_or_none()
                if config:
                    return {
                        "is_enabled": config.is_enabled,
                        "interval_seconds": config.interval_seconds,
                        "notify_telegram": config.notify_telegram,
                        "notify_on_severity": config.notify_on_severity,
                        "config": config.config or {},
                    }
        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Failed to get config: {e}")
        return None

    async def _get_config_from_session(self, session: AsyncSession) -> AgentConfig | None:
        """Отримати конфіг з існуючої сесії."""
        result = await session.execute(
            select(AgentConfig).where(AgentConfig.agent_name == self.AGENT_NAME)
        )
        return result.scalar_one_or_none()

    async def _update_run_stats(self, duration_ms: int):
        """Оновити статистику запусків."""
        try:
            async with async_session_factory() as session:
                await session.execute(
                    update(AgentConfig)
                    .where(AgentConfig.agent_name == self.AGENT_NAME)
                    .values(
                        last_run_at=datetime.now(timezone.utc),
                        total_runs=AgentConfig.total_runs + 1,
                        status=AgentStatus.ACTIVE,
                    )
                )
                await session.commit()
        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Failed to update stats: {e}")

    # ─── Manual Run ───────────────────────────────────────

    async def run_once(self) -> dict:
        """Ручний запуск агента (з дашборду або API). Повертає результат."""
        start_time = time.time()
        try:
            result = await self.execute()
            duration_ms = int((time.time() - start_time) * 1000)
            await self._update_run_stats(duration_ms)
            return {
                "agent": self.AGENT_NAME,
                "status": "success",
                "duration_ms": duration_ms,
                "result": result,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            await self.log(
                action="manual_run_error",
                message=str(e),
                severity=AgentSeverity.ERROR,
                success=False,
                duration_ms=duration_ms,
            )
            return {
                "agent": self.AGENT_NAME,
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(e),
            }
