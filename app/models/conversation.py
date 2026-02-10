"""
Conversation storage for batch analysis (AI Brain Ecosystem).
Stores all bot conversations for learning_engine and analytics.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """Зберігання розмов для batch аналізу."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, default="healer_nexus", index=True)

    # Учасники
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    bot_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "specialist" | "consumer"

    # Розмова
    messages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # [{"role": "user", "text": "..."}, ...]

    # Метрики
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # Результат
    converted: Mapped[bool] = mapped_column(Boolean, default=False)  # Чи записався
    churn_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)  # Чому пішов

    # AI аналіз (заповнюється batch)
    pain_points: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    detected_emotions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ai_insights: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # GDPR
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
