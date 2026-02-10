"""
AI Brain Ecosystem — центральний координатор, role switching, hybrid AI, learning.
Module 2: brain_core, role_switcher, hybrid_provider, learning_engine, knowledge_manager.
"""
from app.ai.brain.brain_core import AIBrainCore
from app.ai.brain.role_switcher import RoleSwitcher
from app.ai.brain.hybrid_provider import HybridAIProvider
from app.ai.brain.learning_engine import LearningEngine
from app.ai.brain.knowledge_manager import KnowledgeManager

__all__ = [
    "AIBrainCore",
    "RoleSwitcher",
    "HybridAIProvider",
    "LearningEngine",
    "KnowledgeManager",
]
