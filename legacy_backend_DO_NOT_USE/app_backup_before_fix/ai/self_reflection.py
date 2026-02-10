from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class ReflectionEngine:
    def __init__(self):
        # Ваги ключових слів для точного визначення
        self.keyword_weights = {
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
        service_scores = {
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

# Створюємо екземпляр для використання в додатку
reflection_engine = ReflectionEngine()
