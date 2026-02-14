"""
Emotion analysis stub for personalized AI bots.
Returns placeholder scores; can be replaced with real ML/NLP later.
Integration: project_id-aware, EventBus can publish analysis events.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class EmotionScore:
    label: str  # e.g. "anxiety", "calm", "curiosity"
    score: float  # 0.0 - 1.0
    confidence: float = 0.0


def analyze_emotions(message: str, project_id: str = "healer_nexus") -> List[EmotionScore]:
    """
    Stub: returns placeholder emotion scores.
    Replace with real model (e.g. transformer or keyword-based) later.
    """
    # Placeholder: simple keyword-based stub
    msg_lower = message.lower()
    stub_scores: List[Tuple[str, float]] = []
    if any(w in msg_lower for w in ["тривога", "страх", "погано", "сумно"]):
        stub_scores.append(("anxiety", 0.7))
    if any(w in msg_lower for w in ["дякую", "добре", "супер"]):
        stub_scores.append(("gratitude", 0.6))
    if not stub_scores:
        stub_scores.append(("neutral", 0.5))

    return [
        EmotionScore(label=label, score=score, confidence=0.5)
        for label, score in stub_scores
    ]


def get_dominant_emotion(message: str, project_id: str = "healer_nexus") -> str:
    """Stub: returns the dominant emotion label for the message."""
    scores = analyze_emotions(message, project_id)
    if not scores:
        return "neutral"
    return max(scores, key=lambda s: s.score).label
