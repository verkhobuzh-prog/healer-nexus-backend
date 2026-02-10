"""Спільні клавіатури для Specialist та Consumer ботів (python-telegram-bot)."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# Ніші для реєстрації спеціаліста та пошуку
SERVICE_TYPES = [
    ("healer", "🧘 Цілитель"),
    ("coach", "💎 Коуч"),
    ("teacher_math", "📐 Математика"),
    ("interior_designer", "🛋️ Дизайн інтер'єру"),
    ("3d_modeling", "🎨 3D"),
    ("web_development", "💻 Веб"),
]


def service_type_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура вибору ніші (service_type)."""
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"service_{key}")]
        for key, label in SERVICE_TYPES
    ]
    return InlineKeyboardMarkup(buttons)


def specialist_main_keyboard() -> ReplyKeyboardMarkup:
    """Головне меню Specialist Bot."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("/profile"), KeyboardButton("/portfolio")],
            [KeyboardButton("/blog"), KeyboardButton("/stats")],
            [KeyboardButton("/promote")],
        ],
        resize_keyboard=True,
    )


def consumer_main_keyboard() -> ReplyKeyboardMarkup:
    """Головне меню Consumer Bot."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("/search"), KeyboardButton("/favorites")],
            [KeyboardButton("/history"), KeyboardButton("/feedback")],
        ],
        resize_keyboard=True,
    )
