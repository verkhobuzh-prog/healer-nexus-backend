"""
Practitioner profiles: per-specialist personalization for AI bots.
Stores empathy ratio, style preferences, and optional persona.
Multi-project: project_id on every row.
"""
from __future__ import annotations

from sqlalchemy import String, Text, Boolean, JSON, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PractitionerProfile(Base, TimestampMixin):
    """Профіль практика для персоналізованих AI-ботів."""

    __tablename__ = "practitioner_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="healer_nexus", index=True
    )
    specialist_id: Mapped[int] = mapped_column(
        ForeignKey("specialists.id"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # 80/20 empathy rule: 80 = empathy/listening weight, 20 = advice weight (stored as ratio 0.0-1.0)
    empathy_ratio: Mapped[float] = mapped_column(
        default=0.8, nullable=False
    )  # 0.8 = 80% empathy
    # Style: "calm" | "energetic" | "educational" | "minimal"
    style: Mapped[str] = mapped_column(String(50), default="calm", nullable=False)
    # Optional persona / tone hints for AI
    persona_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Feature flags / preferences as JSON
    preferences: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Personalization for AI prompts
    unique_story: Mapped[str | None] = mapped_column(Text, nullable=True)
    soft_cta_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_channel_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    creator_signature: Mapped[str] = mapped_column(
        String(255), default="Створено з ❤️ на платформі Healer Nexus", nullable=False
    )
    # Social links: { "telegram": "username", "instagram": "handle", ... } — system builds full URLs
    social_links: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<PractitionerProfile(id={self.id}, specialist_id={self.specialist_id}, project_id={self.project_id})>"
