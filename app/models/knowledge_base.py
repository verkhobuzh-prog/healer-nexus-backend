"""
Knowledge Base — зберігання тренувальних розмов та інсайтів для AI Brain.
Заповнюється pre_seed_learning з data/healers_pre_seed.json.
"""
from __future__ import annotations

from sqlalchemy import String, Text, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KnowledgeBase(Base, TimestampMixin):
    """Записи бази знань: тренувальні розмови та інсайти."""

    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, default="healer_nexus", index=True)

    # Тип: conversation (тренувальна розмова) | insight (готовий інсайт)
    entry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    service_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Контент: повідомлення або інсайт
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
