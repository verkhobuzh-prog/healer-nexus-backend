"""System metrics collection for Healer Nexus. CPU, RAM, disk; threshold alerts + Telegram."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import psutil

from app.config import settings

logger = logging.getLogger(__name__)

# Track last alert time to prevent spam (cooldown: 15 min)
_last_alert: dict[str, datetime] = {}
ALERT_COOLDOWN = timedelta(minutes=15)


async def _send_alert(message: str) -> None:
    """Send alert to admin via Telegram (if bot token configured)."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.ADMIN_CHAT_ID:
        logger.debug("Telegram not configured; skipping alert")
        return

    try:
        import aiohttp
    except ImportError:
        logger.debug("aiohttp not installed; skipping Telegram alert")
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.ADMIN_CHAT_ID,
        "text": f"🚨 *Healer Nexus Alert*\n\n{message}",
        "parse_mode": "Markdown",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    logger.error("Telegram alert failed: HTTP %d", resp.status)
    except Exception as e:
        logger.error("Failed to send Telegram alert: %s", e)


async def collect_system_metrics() -> dict:
    """Collect CPU, RAM, disk metrics asynchronously (blocking psutil in executor)."""
    loop = asyncio.get_event_loop()

    def _sample() -> tuple[float, float, float]:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        return cpu, ram, disk

    cpu, ram, disk = await loop.run_in_executor(None, _sample)

    logger.info(
        "📊 System metrics: CPU=%.1f%%, RAM=%.1f%%, Disk=%.1f%%",
        cpu, ram, disk,
    )

    alerts: list[str] = []
    now = datetime.now()

    # CPU alert with cooldown
    if cpu > settings.CRITICAL_CPU:
        alerts.append(f"⚠️ CPU: {cpu}%")
        if "cpu" not in _last_alert or (now - _last_alert["cpu"]) > ALERT_COOLDOWN:
            await _send_alert(
                f"⚠️ High CPU usage: {cpu:.1f}% (threshold: {settings.CRITICAL_CPU}%)"
            )
            _last_alert["cpu"] = now
            logger.info("📨 Alert sent to admin (type: %s)", "cpu")
        logger.warning("⚠️ High CPU usage: %.1f%%", cpu)

    # RAM alert with cooldown
    if ram > settings.CRITICAL_RAM:
        alerts.append(f"⚠️ RAM: {ram}%")
        if "ram" not in _last_alert or (now - _last_alert["ram"]) > ALERT_COOLDOWN:
            await _send_alert(
                f"⚠️ High RAM usage: {ram:.1f}% (threshold: {settings.CRITICAL_RAM}%)"
            )
            _last_alert["ram"] = now
            logger.info("📨 Alert sent to admin (type: %s)", "ram")
        logger.warning("⚠️ High RAM usage: %.1f%%", ram)

    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "alerts": alerts,
    }
