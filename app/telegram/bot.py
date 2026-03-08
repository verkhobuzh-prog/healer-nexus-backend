import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from app.config import settings

logging.basicConfig(level=logging.INFO)


class HealerAdminBot:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.application = None

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("👋 Адмін-панель активна.")

    async def start(self):
        if not self.token:
            print("❌ TELEGRAM_BOT_TOKEN не знайдено")
            return
        
        self.application = Application.builder().token(self.token).build()
        self.application.add_handler(CommandHandler("start", self.start_cmd))

        await self.application.initialize()
        await self.application.start()
        if os.getenv("TELEGRAM_USE_POLLING", "").lower() not in ("1", "true", "yes"):
            logging.getLogger(__name__).info("HealerAdminBot: polling вимкнено (webhook mode). TELEGRAM_USE_POLLING=1 для polling.")
            return
        await self.application.updater.start_polling()
        print("✅ Telegram Admin Bot працює")

    async def stop(self):
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            print("🛑 Бот зупинений")
