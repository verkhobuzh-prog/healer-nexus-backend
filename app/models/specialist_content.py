"""
Specialist content: blogs, portfolio, product sales (AI Brain Ecosystem).
Content from specialists for feeds and AI promotion.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SpecialistContent(Base, TimestampMixin):
    """Контент від спеціалістів (блоги, портфоліо, продажі)."""

    __tablename__ = "specialist_content"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    specialist_id: Mapped[int] = mapped_column(
        ForeignKey("specialists.id"),
        nullable=False,
        index=True,
    )

    # Тип контенту
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="blog | portfolio_item | product_sale | video",
    )

    # Контент
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_urls: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # Фото/відео

    # Для продажу (художники, дизайнери)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Ціна картини/проекту
    is_for_sale: Mapped[bool] = mapped_column(Boolean, default=False)
    sold: Mapped[bool] = mapped_column(Boolean, default=False)

    # Метрики
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    leads_generated: Mapped[int] = mapped_column(Integer, default=0)  # Скільки запитів

    # AI просування
    ai_promoted: Mapped[bool] = mapped_column(Boolean, default=False)
    promotion_score: Mapped[float] = mapped_column(Float, default=0.0)  # Наскільки просувати
    target_audience: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # ["anxiety_users", "art_lovers"]
