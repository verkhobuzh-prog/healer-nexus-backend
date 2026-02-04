import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app.config import settings
from app.ai.providers import get_ai_provider
from app.services.db_service import save_message, get_history, init_db

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Створюємо кнопки меню
    keyboard = [
        ["🧘 Цілителі", "🎨 Митці"],
        ["📚 Вчителі", "🛠️ Ремонт"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Привіт! Я AI-асистент платформи Healer Nexus. Оберіть категорію або запитайте мене про щось:",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Обробка натискання кнопки "Цілителі"
    if text == "🧘 Цілителі":
        # Тут ми могли б зробити запит до вашого API
        await update.message.reply_text("🧘 У нас є чудові фахівці!\n\nНаприклад:\n- Олена (Йога)\n\nВи можете знайти їх на сайті: http://172.19.209.155:8000")
        return

    # Логіка AI-відповіді
    try:
        history = await get_history(user_id)
        ai = get_ai_provider()
        response = await ai.generate_response(text, history)

        await save_message(user_id, "user", text)
        await save_message(user_id, "assistant", response)
        await update.message.reply_text(response)
    except Exception as e:
        logging.error(f"AI Error: {e}")
        # ВИПРАВЛЕНО: Використовуємо одинарні лапки всередині подвійних
        await update.message.reply_text("Я зараз налаштовую свій 'мозок', спробуйте написати ще раз за хвилину.")

async def main():
    await init_db()
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ Помилка: TELEGRAM_BOT_TOKEN не знайдено!")
        return

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Бот забігав! Перевіряй Telegram.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
