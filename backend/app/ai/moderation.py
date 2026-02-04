from app.ai.providers import get_ai_provider
import logging

logger = logging.getLogger("App.Moderation")

class AutoModeration:
    def __init__(self):
        # Отримуємо провайдера один раз при ініціалізації класу
        self.engine = get_ai_provider()

    async def check_text(self, text: str) -> str:
        prompt = f"""
        Проаналізуй опис профілю цілителя.
        Визнач, чи немає там шахрайства або порушення етики.
        Дай коротку відповідь: 'СХВАЛЕНО' або 'ВІДХИЛЕНО' та поясни чому.
        Текст для перевірки: {text}
        """
        try:
            # Викликаємо метод generate_response (або prompt, залежно від твого провайдера)
            # У новій архітектурі ми використовуємо метод generate_response
            result = await self.engine.generate_response(prompt)
            return result
        except Exception as e:
            logger.error(f"❌ Помилка модерації: {e}")
            return "ПОМИЛКА МОДЕРАЦІЇ: не вдалося зв'язатися з ШІ"
