"""
Start Healer Nexus Telegram bot in a background thread (async-first).
Uses app.telegram.healer_bot as the main entry point.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


def _run_healer_bot() -> None:
    """Entry point for the bot thread: run HealerNexusBot (blocking)."""
    from app.telegram.healer_bot import HealerNexusBot
    bot = HealerNexusBot()
    bot.run()


def start_bot_process() -> threading.Thread:
    """Start Healer Nexus bot in a background thread. Returns the thread (daemon)."""
    logger.info("🚀 Starting Healer Nexus Bot (healer_bot) in background thread")
    thread = threading.Thread(target=_run_healer_bot, daemon=True, name="healer_bot")
    thread.start()
    return thread
