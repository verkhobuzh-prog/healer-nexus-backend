from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class UserIntent(Enum):
    BOOKING = "booking"
    INFORMATION = "information"
    COMPARISON = "comparison"
    EMERGENCY = "emergency"

class ResponseMode(Enum):
    DIRECT = "direct"
    EDUCATIONAL = "educational"
    LISTENING = "listening"

@dataclass
class ClassificationEvent:
    user_id: int
    suggested_service: str
    actual_service: Optional[str] = None
    was_correct: bool = False
    user_feedback: Optional[str] = None

class ReflectionEngine:
    def __init__(self):
        self.keyword_weights: Dict[str, float] = {
            "медитація": 0.9, "енергія": 0.8, "спокій": 0.9, "йога": 0.95,
            "чакра": 0.95, "аура": 0.9, "цілитель": 1.0, "healer": 1.0,
            
            "гроші": 0.9, "трансформація": 0.85, "нейро": 0.8,
            "коуч": 1.0, "розвиток": 0.7, "потенціал": 0.75, "coach": 1.0,
            
            "урок": 0.95, "вчитель": 1.0, "математика": 0.95,
            "українська": 0.9, "навчання": 0.8, "школа": 0.85,
            
            "дизайн": 1.0, "меблі": 0.95, "інтер'єр": 0.9,
            "ремонт": 0.85, "архітектура": 0.9, "стіл": 0.7,
            
            "3d": 1.0, "модель": 0.8, "візуалізація": 0.85,
            "рендер": 0.9, "blender": 0.95,
            
            "сайт": 1.0, "веб": 0.95, "розробка": 0.8,
            "лендінг": 0.9, "website": 1.0, "web": 0.95
        }
        
        self.misclassifications: List[ClassificationEvent] = []
        self.specialist_rankings: Dict[int, Dict[str, float]] = {}
    
    def classify_intent(self, message: str) -> UserIntent:
        """Визначення наміру користувача"""
        msg_lower = message.lower()
        
        if any(w in msg_lower for w in ["терміново", "зараз", "негайно", "дуже погано"]):
            return UserIntent.EMERGENCY
        
        if any(w in msg_lower for w in ["записатись", "запис", "коли", "ціна", "скільки коштує"]):
            return UserIntent.BOOKING
        
        if any(w in msg_lower for w in ["порівняти", "різниця", "краще", "хто кращий"]):
            return UserIntent.COMPARISON
        
        return UserIntent.INFORMATION
    
    def detect_service(self, message: str) -> Tuple[str, float]:
        """
        ✅ Визначення service_type з confidence score
        Returns: (service_type, confidence)
        """
        msg_lower = message.lower()
        
        service_scores = {
            "healer": 0.0,
            "coach": 0.0,
            "teacher_math": 0.0,
            "teacher_ukrainian": 0.0,
            "interior_designer": 0.0,
            "3d_modeling": 0.0,
            "web_development": 0.0
        }
        
        for keyword, weight in self.keyword_weights.items():
            if keyword in msg_lower:
                if keyword in ["медитація", "енергія", "спокій", "йога", "чакра", "аура", "цілитель", "healer"]:
                    service_scores["healer"] += weight
                elif keyword in ["гроші", "трансформація", "нейро", "коуч", "розвиток", "потенціал", "coach"]:
                    service_scores["coach"] += weight
                elif keyword in ["урок", "вчитель", "математика", "навчання", "школа"] and "українська" not in msg_lower:
                    service_scores["teacher_math"] += weight
                elif keyword in ["урок", "вчитель", "українська", "навчання", "мова"]:
                    service_scores["teacher_ukrainian"] += weight
                elif keyword in ["дизайн", "меблі", "інтер'єр", "ремонт", "архітектура", "стіл"]:
                    service_scores["interior_designer"] += weight
                elif keyword in ["3d", "модель", "візуалізація", "рендер", "blender"]:
                    service_scores["3d_modeling"] += weight
                elif keyword in ["сайт", "веб", "розробка", "лендінг", "website", "web"]:
                    service_scores["web_development"] += weight
        
        best_service = max(service_scores.items(), key=lambda x: x[1])
        confidence = min(best_service[1], 1.0)
        
        if confidence < 0.3:
            return "healer", 0.3
        
        return best_service[0], confidence
    
    def calculate_anxiety_score(self, message: str) -> float:
        """Оцінка рівня тривожності (0.0 - 1.0)"""
        msg_lower = message.lower()
        
        anxiety_keywords = {
            "не знаю": 0.3,
            "боюсь": 0.5,
            "страшно": 0.6,
            "тривога": 0.7,
            "паніка": 0.8,
            "допоможіть": 0.4,
            "не впевнений": 0.4,
            "сумніваюсь": 0.3
        }
        
        score = 0.0
        for keyword, weight in anxiety_keywords.items():
            if keyword in msg_lower:
                score = max(score, weight)
        
        if msg_lower.count("!") > 2:
            score += 0.2
        
        return min(score, 1.0)
    
    def record_misclassification(self, event: ClassificationEvent):
        """Запис помилки класифікації"""
        self.misclassifications.append(event)
        logger.warning(
            f"❌ MISCLASSIFICATION: suggested={event.suggested_service}, "
            f"actual={event.actual_service} for user {event.user_id}"
        )
    
    def get_response_mode(
        self,
        user_intent: UserIntent,
        anxiety_score: float,
        negative_feedback: bool = False
    ) -> ResponseMode:
        """Вибір режиму відповіді"""
        if negative_feedback:
            return ResponseMode.LISTENING
        
        if user_intent == UserIntent.EMERGENCY:
            return ResponseMode.DIRECT
        
        if anxiety_score > 0.6:
            return ResponseMode.LISTENING
        
        if user_intent == UserIntent.INFORMATION:
            return ResponseMode.EDUCATIONAL
        
        return ResponseMode.DIRECT
    
    def rank_specialists(
        self,
        user_id: int,
        service_type: str,
        anxiety_score: float
    ) -> List[str]:
        """Ранжування спеціалістів"""
        specialists = {
            "healer": ["Антон", "Ігор", "Марія"],
            "coach": ["Анна", "Петро"],
            "teacher_math": ["Лариса", "Олена"],
            "teacher_ukrainian": ["Наталія", "Іван"],
            "interior_designer": ["Катерина", "Сергій"],
            "3d_modeling": ["AI 3D Generator", "Максим"],
            "web_development": ["AI Website Builder", "Андрій"]
        }
        
        service_specialists = specialists.get(service_type, [])
        
        if anxiety_score > 0.6:
            service_specialists = list(reversed(service_specialists))
        
        return service_specialists
    
    def generate_smart_link(
        self,
        service_type: str,
        top_specialist: Optional[str] = None,
        mode: ResponseMode = ResponseMode.DIRECT
    ) -> str:
        """Генерація персоналізованого посилання"""
        if mode == ResponseMode.EDUCATIONAL:
            return f"/blog?category={service_type}"
        
        base_link = f"/dashboard?service_type={service_type}"
        
        if top_specialist and mode == ResponseMode.DIRECT:
            base_link += f"&top={top_specialist}"
        
        return base_link

reflection_engine = ReflectionEngine()
