import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from sqlalchemy import select
from datetime import datetime, timezone

from app.config import settings
from app.database.connection import async_session_maker
from app.models.user import User
from app.models.message import Message
from app.ai.providers import get_ai_provider

logger = logging.getLogger(__name__)

_bot_instance = None


class HealerNexusBot:
    def __init__(self):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")

        proxy_url = getattr(settings, "TELEGRAM_PROXY", None) or ""

        if proxy_url:
            # Proxy mode: create HTTPXRequest with timeouts built-in
            from telegram.request import HTTPXRequest
            request = HTTPXRequest(
                proxy=proxy_url,
                connection_pool_size=8,
                connect_timeout=30.0,
                read_timeout=60.0,
                write_timeout=30.0,
                pool_timeout=30.0,
            )
            self.application = (
                Application.builder()
                .token(settings.TELEGRAM_BOT_TOKEN)
                .request(request)
                .build()
            )
            logger.info("✅ Using proxy: %s", proxy_url)
        else:
            # No proxy: use builder timeouts
            self.application = (
                Application.builder()
                .token(settings.TELEGRAM_BOT_TOKEN)
                .connect_timeout(30)
                .read_timeout(60)
                .write_timeout(30)
                .pool_timeout(30)
                .build()
            )

        self.db_session_maker = async_session_maker
        self.current_role = {}

        global _bot_instance
        _bot_instance = self

    def _register_handlers(self):
        """Register handlers (used by both run_polling and webhook)."""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def get_or_create_user(self, session, tg_user):
        """Отримати або створити користувача"""
        result = await session.execute(
            select(User).where(User.telegram_id == tg_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=tg_user.id,
                username=tg_user.username,
                requests_left=5  # 5 безкоштовних запитів
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Головне меню"""
        user_tg = update.effective_user
        
        async with async_session_maker() as session:
            user = await self.get_or_create_user(session, user_tg)
            
        is_admin = str(user_tg.id) == settings.ADMIN_CHAT_ID
        
        text = f"🌟 <b>Healer Nexus</b>\n\nВітаємо, {user_tg.first_name}!\n"
        
        if not is_admin:
            text += f"У вас залишилось <b>{user.requests_left}</b> безкоштовних запитів.\n\n"
        else:
            text += "🚀 <b>Admin Mode</b> (Unlimited)\n\n"
        
        text += "Оберіть категорію:"
        
        keyboard = [
            [InlineKeyboardButton("🧘 Цілителі", callback_data="role_healer")],
            [InlineKeyboardButton("💎 Коучі", callback_data="role_transformational_coach")],
            [InlineKeyboardButton("📚 Вчителі", callback_data="role_education")],
            [InlineKeyboardButton("🛋️ Дизайнери", callback_data="role_designer")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка кнопок"""
        query = update.callback_query
        await query.answer()
        
        role = query.data.replace("role_", "")
        self.current_role[query.from_user.id] = role
        
        role_names = {
            "healer": "🧘 Цілитель",
            "transformational_coach": "💎 Коуч",
            "education": "📚 Вчитель",
            "designer": "🛋️ Дизайнер"
        }
        
        await query.edit_message_text(
            f"✅ Обрано: {role_names.get(role, 'default')}\n\n"
            "Тепер пишіть ваші запитання! 💬"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка повідомлень з лімітами"""
        user_tg = update.effective_user
        user_text = update.message.text
        role = self.current_role.get(user_tg.id, "default")

        async with async_session_maker() as session:
            user = await self.get_or_create_user(session, user_tg)
            is_admin = str(user_tg.id) == settings.ADMIN_CHAT_ID

            # Перевірка лімітів
            if not user.can_make_request() and not is_admin:
                await update.message.reply_text(
                    "❌ Ліміт безкоштовних запитів вичерпано.\n\n"
                    "💎 Оформіть підписку: /subscribe"
                )
                return

            try:
                # Отримуємо історію (останні 10 повідомлень)
                result = await session.execute(
                    select(Message)
                    .where(Message.user_id == user.id)
                    .order_by(Message.created_at.desc())
                    .limit(10)
                )
                messages = result.scalars().all()
                history = [
                    {"role": m.role, "content": m.content}
                    for m in reversed(messages)
                ]
                
                # AI відповідь (generate_response повертає dict з "text" та "metadata")
                ai = get_ai_provider()
                result = await ai.generate_response(
                    user_text, history, role,
                    user_id=user.id,
                    db=session,
                )
                response_text = result["text"]

                # Зберігаємо в БД
                user_msg = Message(user_id=user.id, role="user", content=user_text)
                ai_msg = Message(user_id=user.id, role="assistant", content=response_text)
                session.add(user_msg)
                session.add(ai_msg)

                # Оновлюємо лічильники
                if not is_admin:
                    user.requests_left -= 1
                user.total_requests += 1

                await session.commit()

                # Відповідь користувачу
                suffix = f"\n\n<i>Залишилось: {user.requests_left}</i>" if not is_admin else ""
                await update.message.reply_text(f"{response_text}{suffix}", parse_mode="HTML")
                
            except Exception as e:
                await update.message.reply_text(f"❌ Помилка: {str(e)}")

    def run(self):
        """Запуск бота"""
        self._register_handlers()
        print("🚀 Healer Nexus Bot запущено з лімітами")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


async def process_update(data: dict) -> None:
    """Process incoming Telegram update from webhook."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = HealerNexusBot()
        _bot_instance._register_handlers()
        await _bot_instance.application.initialize()
        await _bot_instance.application.start()

    update = Update.de_json(data, _bot_instance.application.bot)
    if update:
        await _bot_instance.application.process_update(update)


if __name__ == "__main__":
    bot = HealerNexusBot()
    bot.run()
