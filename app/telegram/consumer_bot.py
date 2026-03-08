"""
Consumer Bot — для клієнтів, які шукають послуги.
Пошук спеціалістів, AI-рекомендації (більові точки), бронювання, відгуки.
Токен: HEALER_CONSUMER_BOT_TOKEN.
"""
from __future__ import annotations

import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from sqlalchemy import select

from app.config import settings
from app.database.connection import async_session_maker
from app.models.specialist import Specialist
from app.telegram.shared.keyboards import consumer_main_keyboard, service_type_keyboard
from app.telegram.shared.handlers import get_or_create_user
from app.ai.brain.brain_core import AIBrainCore

logger = logging.getLogger(__name__)


class ConsumerBot:
    """Бот для клієнтів: пошук, рекомендації, бронювання, відгуки."""

    def __init__(self) -> None:
        token = getattr(settings, "HEALER_CONSUMER_BOT_TOKEN", None) or ""
        if not token:
            token = settings.TELEGRAM_BOT_TOKEN
        self.app = (
            Application.builder()
            .token(token)
            .connect_timeout(30)
            .read_timeout(60)
            .write_timeout(30)
            .pool_timeout(30)
            .build()
        )
        self.brain = AIBrainCore()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/start — вітання та головне меню."""
        user = update.effective_user
        if not user:
            return
        async with async_session_maker() as session:
            await get_or_create_user(session, user.id, user.username)
        await update.message.reply_text(
            f"👋 Вітаємо, {user.first_name or 'гость'}!\n\n"
            "Тут ви можете знайти спеціалістів, отримати рекомендації та забронювати послугу.",
            reply_markup=consumer_main_keyboard(),
        )

    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/search — пошук спеціалістів за нішею."""
        await update.message.reply_text(
            "Оберіть категорію:",
            reply_markup=service_type_keyboard(),
        )

    async def callback_search_by_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрано категорію пошуку — показати список спеціалістів."""
        query = update.callback_query
        if not query or not query.data or not query.from_user:
            return
        await query.answer()
        service_type = query.data.replace("service_", "")
        async with async_session_maker() as session:
            result = await session.execute(
                select(Specialist)
                .where(Specialist.service_type == service_type, Specialist.is_active == True)
                .limit(20)
            )
            specialists = result.scalars().all()
        if not specialists:
            await query.edit_message_text(
                f"По категорії «{service_type}» поки немає спеціалістів. Спробуйте пізніше або іншу категорію."
            )
            return
        lines = []
        for s in specialists:
            rate = f"{s.hourly_rate} грн/год" if s.hourly_rate else "—"
            link = f" | [Портфоліо]({s.portfolio_url})" if s.portfolio_url else ""
            lines.append(f"• **{s.name}** — {rate}{link}")
        text = "🔍 Результати пошуку:\n\n" + "\n".join(lines)
        await query.edit_message_text(text[:4000], parse_mode="Markdown")

    async def favorites(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/favorites — обране (заглушка)."""
        await update.message.reply_text("Обране: збережені спеціалісти будуть у наступній версії.")

    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/history — історія бронювань (заглушка)."""
        await update.message.reply_text("Історія бронювань буде доступна після реалізації бронювання.")

    async def feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/feedback — залишити відгук (заглушка)."""
        await update.message.reply_text(
            "Відгуки: після завершення сесії ви зможете залишити оцінку. Поки що — напишіть у підтримку."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Вільне повідомлення — AI (більові точки, рекомендації)."""
        if not update.message or not update.message.text or not update.effective_user:
            return
        ctx = {"user_id": update.effective_user.id, "history": [], "role": "default", "db": None}
        try:
            async with async_session_maker() as db:
                ctx["db"] = db
                out = await self.brain.process_user_message(
                    update.message.text, ctx, bot_type="consumer"
                )
            text = out.get("text", "Немає відповіді.") if isinstance(out, dict) else str(out)
            await update.message.reply_text(text[:4000])
        except Exception:
            logger.exception("ConsumerBot: помилка AI")
            await update.message.reply_text("Помилка обробки. Спробуйте /search або /start.")

    def run(self) -> None:
        """Запуск поллінгу."""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("search", self.search))
        self.app.add_handler(CommandHandler("favorites", self.favorites))
        self.app.add_handler(CommandHandler("history", self.history))
        self.app.add_handler(CommandHandler("feedback", self.feedback))
        self.app.add_handler(CallbackQueryHandler(self.callback_search_by_type))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        if os.getenv("TELEGRAM_USE_POLLING", "").lower() not in ("1", "true", "yes"):
            logger.info(
                "ConsumerBot: polling вимкнено (webhook mode). "
                "Для локального polling встановіть TELEGRAM_USE_POLLING=1"
            )
            return
        logger.info("ConsumerBot: запуск поллінгу")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ConsumerBot().run()
