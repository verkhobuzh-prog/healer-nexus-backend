"""
Specialist Bot — для цілителів, художників, вчителів.
Реєстрація, контент (блог, портфоліо), статистика, AI-рекомендації.
Токен: HEALER_SPECIALIST_BOT_TOKEN.
"""
from __future__ import annotations

import logging
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
from app.telegram.shared.keyboards import specialist_main_keyboard, service_type_keyboard
from app.telegram.shared.handlers import get_or_create_user, get_specialist_by_telegram_id
from app.ai.brain.brain_core import AIBrainCore

logger = logging.getLogger(__name__)


class SpecialistBot:
    """Бот для спеціалістів: реєстрація, портфоліо, блог, статистика, AI-рекомендації."""

    def __init__(self) -> None:
        token = getattr(settings, "HEALER_SPECIALIST_BOT_TOKEN", None) or settings.TELEGRAM_BOT_TOKEN
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
        self._registration_state: dict[int, dict] = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/start — реєстрація або вхід; показати головне меню."""
        user = update.effective_user
        if not user:
            return
        async with async_session_maker() as session:
            await get_or_create_user(session, user.id, user.username)
        spec = await get_specialist_by_telegram_id(user.id)
        if spec:
            await update.message.reply_text(
                f"🌟 Вітаємо знову, {spec.name}!\n\n"
                "Ваш профіль активний. Скористайтесь меню нижче.",
                reply_markup=specialist_main_keyboard(),
            )
            logger.info("SpecialistBot: вхід спеціаліста id=%s", spec.id)
        else:
            self._registration_state[user.id] = {"step": "name"}
            await update.message.reply_text(
                "👋 Реєстрація спеціаліста.\nНапишіть ваше ім'я (як для клієнтів):"
            )

    async def handle_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обробка кроків реєстрації: name → service_type → price → portfolio."""
        user = update.effective_user
        if not user or not update.message or not update.message.text:
            return
        state = self._registration_state.get(user.id)
        if not state:
            return
        text = update.message.text.strip()
        step = state.get("step")

        if step == "name":
            state["name"] = text[:255]
            state["step"] = "service_type"
            await update.message.reply_text(
                "Оберіть нішу:",
                reply_markup=service_type_keyboard(),
            )
            return

        if step == "price":
            try:
                price = int(text)
                if price < 0:
                    raise ValueError("Ціна не може бути від'ємною")
            except ValueError:
                await update.message.reply_text("Введіть число (ціна за годину, грн):")
                return
            state["hourly_rate"] = price
            state["step"] = "portfolio"
            await update.message.reply_text("Посилання на портфоліо (або напишіть -):")
            return

        if step == "portfolio":
            state["portfolio_url"] = text if text != "-" else None
            del self._registration_state[user.id]
            async with async_session_maker() as session:
                spec = Specialist(
                    name=state["name"],
                    service_type=state.get("service_type", "healer"),
                    delivery_method="human",
                    specialty=state.get("specialty", "Спеціаліст"),
                    hourly_rate=state.get("hourly_rate", 0),
                    portfolio_url=state.get("portfolio_url"),
                    telegram_id=user.id,
                    is_active=True,
                )
                session.add(spec)
                await session.commit()
                await session.refresh(spec)
            await update.message.reply_text(
                f"✅ Реєстрацію завершено. Вітаємо, {spec.name}!",
                reply_markup=specialist_main_keyboard(),
            )
            logger.info("SpecialistBot: зареєстровано спеціаліста id=%s", spec.id)
            return

    async def callback_service_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрано нішу під час реєстрації."""
        query = update.callback_query
        if not query or not query.data or not query.from_user:
            return
        await query.answer()
        state = self._registration_state.get(query.from_user.id)
        if not state or state.get("step") != "service_type":
            return
        state["service_type"] = query.data.replace("service_", "")
        state["specialty"] = state["service_type"]
        state["step"] = "price"
        await query.edit_message_text(text="Введіть ціну за годину (грн), число:")

    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/profile — мій профіль."""
        user = update.effective_user
        if not user:
            return
        spec = await get_specialist_by_telegram_id(user.id)
        if not spec:
            await update.message.reply_text("Спочатку пройдіть реєстрацію: /start")
            return
        await update.message.reply_text(
            f"📋 <b>Профіль</b>\n"
            f"Ім'я: {spec.name}\n"
            f"Ніша: {spec.service_type}\n"
            f"Ціна: {spec.hourly_rate} грн/год\n"
            f"Портфоліо: {spec.portfolio_url or '—'}",
            parse_mode="HTML",
        )

    async def portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/portfolio — управління портфоліо (заглушка)."""
        await update.message.reply_text("Портфоліо: додавання робіт буде доступне в оновленні. Поки що посилання в профілі /profile")

    async def blog(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/blog — написати статтю (заглушка)."""
        await update.message.reply_text("Блог: написання статей буде в наступній версії.")

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/stats — моя статистика (заглушка)."""
        user = update.effective_user
        if not user:
            return
        spec = await get_specialist_by_telegram_id(user.id)
        if not spec:
            await update.message.reply_text("Спочатку /start")
            return
        await update.message.reply_text(
            f"📊 Статистика для {spec.name}\nПерегляди портфоліо: буде після підключення аналітики.\nLeads: —"
        )

    async def promote(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/promote — налаштування просування та AI-рекомендації."""
        await update.message.reply_text(
            "🤖 AI-рекомендація: додайте фото робіт у профіль для кращої конверсії. "
            "Детальні поради — в оновленні."
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Текст: крок реєстрації або вільне повідомлення (AI)."""
        if not update.message or not update.message.text or not update.effective_user:
            return
        state = self._registration_state.get(update.effective_user.id)
        if state and state.get("step") in ("name", "price", "portfolio"):
            await self.handle_registration(update, context)
            return
        # Вільне повідомлення — AI
        ctx = {"user_id": update.effective_user.id, "history": [], "role": "default", "db": None}
        try:
            async with async_session_maker() as db:
                ctx["db"] = db
                out = await self.brain.process_user_message(
                    update.message.text, ctx, bot_type="specialist"
                )
            text = out.get("text", "Немає відповіді.") if isinstance(out, dict) else str(out)
            await update.message.reply_text(text[:4000])
        except Exception:
            logger.exception("SpecialistBot: помилка AI")
            await update.message.reply_text("Помилка обробки. Спробуйте /start або /profile.")

    def run(self) -> None:
        """Запуск поллінгу."""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("profile", self.profile))
        self.app.add_handler(CommandHandler("portfolio", self.portfolio))
        self.app.add_handler(CommandHandler("blog", self.blog))
        self.app.add_handler(CommandHandler("stats", self.stats))
        self.app.add_handler(CommandHandler("promote", self.promote))
        self.app.add_handler(CallbackQueryHandler(self.callback_service_type))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        logger.info("SpecialistBot: запуск поллінгу")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    SpecialistBot().run()
