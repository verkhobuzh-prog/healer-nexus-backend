"""
Agent audit log: records actions from Gemini, PromoterX, blog scheduler, etc.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AgentAuditLog(Base, TimestampMixin):
    __tablename__ = "agent_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    agent: Mapped[str] = mapped_column(String(50))
    # "gemini" | "promoterx" | "blog_scheduler"
    action: Mapped[str] = mapped_column(String(100))
    # "report_sent" | "post_generated" | "booking_notified"
    status: Mapped[str] = mapped_column(String(20))
    # "success" | "error" | "skipped"
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
