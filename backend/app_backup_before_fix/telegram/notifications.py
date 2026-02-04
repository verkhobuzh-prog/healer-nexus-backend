from app.telegram.bot import TelegramBot

_bot_instance = None

def get_bot() -> TelegramBot:
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBot()
    return _bot_instance

async def send_alert(message: str):
    bot = get_bot()
    await bot.send_message(message)
