"""Reflection engine for intent and service detection. Python 3.13 / PEP 695 friendly."""
from __future__ import annotations

from enum import Enum
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class UserIntent(Enum):
    SEEKING_HELP = "seeking_help"
    BROWSING = "browsing"
    URGENT = "urgent"


class ResponseMode(Enum):
    EMPATHETIC = "empathetic"
    PROFESSIONAL = "professional"
    LISTENING = "listening"


class ReflectionEngine:
    def __init__(self) -> None:
        # Ваги ключових слів для точного визначення (explicit type for 3.13)
        self.keyword_weights: dict[str, float] = {
            "медитація": 0.5, "енергія": 0.6, "чакра": 0.8, "аура": 0.7, 
            "цілитель": 0.9, "карма": 0.4, "спокій": 0.3,
            "гроші": 0.4, "коуч": 0.8, "розвиток": 0.4,
            "трикутник": 0.9, "функція": 0.8, "математика": 1.0, "задача": 0.5,
            "ремонт": 0.7, "інтер'єр": 0.9, "дизайн": 0.5,
            "3d": 0.9, "модель": 0.7, "рендер": 0.8,
            "сайт": 0.7, "додаток": 0.8, "програмування": 0.9
        }

    def detect_service(self, message: str) -> Tuple[str, float]:
        """
        Визначення service_type з confidence score
        """
        msg_lower = message.lower()

        # Ініціалізація балів (Включаючи нові ніші)
        service_scores: dict[str, float] = {
            "healer": 0.0,
            "energy_practitioner": 0.0,
            "coach": 0.0,
            "teacher_math": 0.0,
            "teacher_ukrainian": 0.0,
            "interior_design": 0.0,
            "visual3d": 0.0,
            "web_development": 0.0
        }

        for keyword, weight in self.keyword_weights.items():
            if keyword in msg_lower:
                # Духовні практики
                if keyword in ["медитація", "енергія", "спокій", "йога", "чакра", "аура", "цілитель"]:
                    service_scores["healer"] += weight
                    service_scores["energy_practitioner"] += weight * 0.8
                
                # Математика
                elif keyword in ["трикутник", "функція", "математика", "задача"]:
                    service_scores["teacher_math"] += weight
                
                # Решта категорій...
                elif keyword in ["коуч", "гроші", "розвиток"]:
                    service_scores["coach"] += weight

        # Визначаємо найкращий результат
        best_service, score = max(service_scores.items(), key=lambda x: x[1])
        confidence = min(score, 1.0)

        if confidence < 0.3:
            return "healer", 0.3
        
        return best_service, confidence

    # ✅ FIXED: АЛІАС ДЛЯ СУМІСНОСТІ (щоб не було AttributeError)
    def detect_niche(self, message: str) -> Tuple[str, float]:
        return self.detect_service(message)

    def classify_intent(self, message: str) -> UserIntent:
        """
        Класифікує намір користувача на основі ключових слів
        """
        msg_lower = message.lower()
        
        # Перевірка на терміновість
        urgent_keywords = ["терміново", "допоможіть", "болить", "погано"]
        if any(keyword in msg_lower for keyword in urgent_keywords):
            return UserIntent.URGENT
        
        # Перевірка на пошук допомоги
        help_keywords = ["потрібен", "шукаю", "хочу", "допоможіть"]
        if any(keyword in msg_lower for keyword in help_keywords):
            return UserIntent.SEEKING_HELP
        
        # За замовчуванням - перегляд
        return UserIntent.BROWSING

    def calculate_anxiety_score(self, message: str) -> float:
        """
        Обчислює рівень тривоги на основі ключових слів (0-10)
        """
        anxiety_words: dict[str, float] = {
            "паніка": 10,
            "страх": 8,
            "тривога": 7,
            "переживаю": 6,
            "болить": 7,
            "погано": 6
        }
        
        msg_lower = message.lower()
        max_score: float = 0.0

        for word, score in anxiety_words.items():
            if word in msg_lower:
                max_score = max(max_score, score)
        
        return max_score

    def get_response_mode(self, intent: UserIntent, anxiety: float) -> ResponseMode:
        """
        Визначає режим відповіді на основі наміру та рівня тривоги
        """
        if anxiety > 6 or intent == UserIntent.URGENT:
            return ResponseMode.EMPATHETIC
        
        if intent == UserIntent.SEEKING_HELP:
            return ResponseMode.PROFESSIONAL
        
        return ResponseMode.LISTENING

    def generate_smart_link(self, service_type: str, specialist_name: str | None, mode: ResponseMode) -> str:
        """
        Генерує розумне посилання на основі типу послуги, імені спеціаліста та режиму відповіді
        """
        if specialist_name:
            return f"/specialists/{service_type}/{specialist_name}"
        else:
            return f"/specialists/{service_type}"

# Створюємо екземпляр для використання в додатку
reflection_engine = ReflectionEngine()
