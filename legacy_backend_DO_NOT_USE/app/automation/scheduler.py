import asyncio
from app.telegram.notifications import get_bot
from app.config import settings

async def start_background_tasks():
    """Центральна функція запуску фонових процесів"""
    print("🚀 Ініціалізація фонових завдань...")
    
    # 1. Запуск Telegram бота
    if settings.TELEGRAM_BOT_TOKEN:
        try:
            bot = get_bot()
            await bot.start()
            # Запускаємо прослуховування повідомлень (polling) як фонову задачу
            asyncio.create_task(bot.polling())
            print("✅ Telegram bot polling успішно запущено")
        except Exception as e:
            print(f"❌ Помилка запуску бота: {e}")
    
    # Тут ми пізніше додамо циклічні завдання (cron)
    print("✅ Усі фонові системи активні")
