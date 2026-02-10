import re

# Слова, які перетворюють коучинг на незаконну медицину
STOP_WORDS = ["лікування", "діагноз", "рецепт", "ліки", "вилікую", "терапія"]

def check_compliance(text: str) -> bool:
    """Перевірка на наявність медичних тверджень"""
    text_lower = text.lower()
    for word in STOP_WORDS:
        if re.search(rf"\b{word}\b", text_lower):
            return False
    return True

def apply_disclaimer(text: str) -> str:
    """Додає обов'язкове попередження"""
    disclaimer = "\n\n---\n⚠️ Ця порада має інформаційний характер і не є медичною консультацією."
    return text + disclaimer
