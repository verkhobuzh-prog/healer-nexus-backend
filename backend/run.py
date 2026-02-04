import asyncio
import logging
import sys

# Налаштування логів
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("HealerRunner")

# Імпортуємо головні функції обох модулів
from app.admin_agent.main import main as admin_main
# Переконайся, що шлях до бота вірний (зазвичай це app/telegram/bot.py або app/bot/handlers.py)
try:
    from app.telegram.bot import main as healer_bot_main 
except ImportError:
    # Якщо бот лежить в іншому місці, підкоригуй шлях:
    from app.bot.handlers import main as healer_bot_main 

async def start_all():
    logger.info("🪐 Запуск екосистеми Healer AI (Admin + Client Bot)...")
    
    # Створюємо завдання
    admin_task = asyncio.create_task(admin_main())
    healer_task = asyncio.create_task(healer_bot_main())
    
    # Запускаємо паралельно
    await asyncio.gather(admin_task, healer_task)

if __name__ == "__main__":
    try:
        asyncio.run(start_all())
    except KeyboardInterrupt:
        logger.info("🛑 Зупинка серверів за командою користувача...")
