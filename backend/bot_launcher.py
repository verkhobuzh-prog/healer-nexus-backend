import asyncio
import logging
import sys
import os

# Додаємо поточну директорію в шлях, щоб бот бачив папку 'app'
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from app.config import settings

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bot_launcher")

async def main():
    # 1. Перевірка токена
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or ":" not in token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не знайдено або він невалідний!")
        logger.info("Будь ласка, оновіть токен у файлі .env")
        return

    # 2. Ініціалізація бота
    bot = Bot(token=token)
    dp = Dispatcher()

    # 3. Обробник команди /start
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer(
            f"👋 Привіт! Я Healer Nexus Bot.\n"
            f"✅ Система: {settings.PROJECT_ID}\n"
            f"🚀 Статус: Online"
        )

    # 4. Обробник звичайних повідомлень (Ехо)
    @dp.message()
    async def echo_message(message: types.Message):
        await message.answer(f"Ви написали: {message.text}")

    logger.info("🚀 Бот виходить на зв'язок...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"💥 Критична помилка бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот зупинений користувачем")