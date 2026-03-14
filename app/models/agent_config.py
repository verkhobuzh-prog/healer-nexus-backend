"""
Agent Configuration & Log Models
Зберігає конфігурацію агентів та їх логи роботи.
"""
from __future__ import annotations
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, Boolean, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


class AgentSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AgentConfig(Base):
    """Конфігурація кожного AI-агента."""
    __tablename__ = "agent_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(50), default="healer_nexus")

    # Ідентифікація
    agent_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="health_check | security | qa_tester | bug_scanner | advisor | task_runner"
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Стан
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.PAUSED
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Розклад
    interval_seconds: Mapped[int] = mapped_column(Integer, default=300)  # 5 хв по замовчуванню
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Налаштування (JSON)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Сповіщення
    notify_telegram: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_severity: Mapped[str] = mapped_column(
        String(20), default="warning",
        comment="info | warning | error | critical"
    )

    # Статистика
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_issues_found: Mapped[int] = mapped_column(Integer, default=0)
    total_issues_fixed: Mapped[int] = mapped_column(Integer, default=0)

    # Часи
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AgentLog(Base):
    """Лог роботи AI-агента — кожна дія записується тут."""
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(50), default="healer_nexus")

    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[AgentSeverity] = mapped_column(
        Enum(AgentSeverity), default=AgentSeverity.INFO
    )

    # Що сталось
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Результат
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Telegram сповіщення
    telegram_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
