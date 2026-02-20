"""
Specialist recommendation funnel: track recommended → details_viewed → booked → links_revealed → link_clicks.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SpecialistRecommendation(Base):
    __tablename__ = "specialist_recommendations"
    __table_args__ = (
        Index("ix_spec_rec_project_specialist", "project_id", "specialist_id"),
        Index("ix_spec_rec_specialist_recommended", "specialist_id", "recommended_at"),
        Index("ix_spec_rec_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    specialist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("specialists.id"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="chat")
    recommended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details_viewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    booked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    booking_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    links_revealed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    links_revealed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    link_clicks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
