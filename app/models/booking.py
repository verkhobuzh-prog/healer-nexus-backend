"""
Bookings: user appointments with specialists. Created via chat or API.
Multi-tenant by project_id. FKs no CASCADE.
"""
from __future__ import annotations

import enum
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Booking(Base, TimestampMixin):
    """User booking with a specialist."""

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    specialist_id: Mapped[int] = mapped_column(
        ForeignKey("specialists.id"),
        nullable=False,
        index=True,
    )
    practitioner_id: Mapped[int | None] = mapped_column(
        ForeignKey("practitioner_profiles.id"),
        nullable=True,
        index=True,
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=BookingStatus.PENDING.value,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    specialist_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contact_method: Mapped[str] = mapped_column(String(50), default="telegram", nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_bookings_project_status", "project_id", "status"),
        Index("ix_bookings_specialist_status", "specialist_id", "status"),
        Index("ix_bookings_user_created", "user_id", "created_at"),
        {"sqlite_autoincrement": True},
    )
