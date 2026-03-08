"""
Запуск Specialist та Consumer ботів одночасно.
Кожен бот у власному потоці; якщо токен порожній — бот не запускається.
Таймаути як у healer_bot: connect 30s, read 60s.
Щоб не видаляти webhook, polling запускається лише при TELEGRAM_USE_POLLING=1.
"""
from __future__ import annotations

import logging
import os
import threading

from app.config import settings

logger = logging.getLogger(__name__)


def _run_specialist_bot() -> None:
    """Запуск Specialist Bot у потоці."""
    from app.telegram.specialist_bot import SpecialistBot
    bot = SpecialistBot()
    logger.info("SpecialistBot thread started")
    bot.run()


def _run_consumer_bot() -> None:
    """Запуск Consumer Bot у потоці."""
    from app.telegram.consumer_bot import ConsumerBot
    bot = ConsumerBot()
    logger.info("ConsumerBot thread started")
    bot.run()


def run_both_bots() -> None:
    """Запустити обидва боти одночасно (окремі потоки). Порожні токени пропускаються. Без TELEGRAM_USE_POLLING=1 не запускає polling (webhook mode)."""
    if os.getenv("TELEGRAM_USE_POLLING", "").lower() not in ("1", "true", "yes"):
        logger.info("bot_runner: polling вимкнено (webhook mode). Встановіть TELEGRAM_USE_POLLING=1 для запуску ботів.")
        return
    specialist_token = getattr(settings, "HEALER_SPECIALIST_BOT_TOKEN", None) or ""
    consumer_token = getattr(settings, "HEALER_CONSUMER_BOT_TOKEN", None) or ""

    if specialist_token:
        t1 = threading.Thread(target=_run_specialist_bot, name="SpecialistBot", daemon=True)
        t1.start()
        logger.info("Specialist bot started (HEALER_SPECIALIST_BOT_TOKEN)")
    else:
        logger.warning("HEALER_SPECIALIST_BOT_TOKEN не задано — Specialist bot не запущено")

    if consumer_token:
        t2 = threading.Thread(target=_run_consumer_bot, name="ConsumerBot", daemon=True)
        t2.start()
        logger.info("Consumer bot started (HEALER_CONSUMER_BOT_TOKEN)")
    else:
        logger.warning("HEALER_CONSUMER_BOT_TOKEN не задано — Consumer bot не запущено")

    if not specialist_token and not consumer_token:
        logger.warning("Жоден з токенів Specialist/Consumer не заданий — боти не запущені")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_both_bots()
    # Потоки daemon — головний процес має жити
    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
