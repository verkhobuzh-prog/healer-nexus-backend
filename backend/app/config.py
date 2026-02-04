"""
Application configuration and structured logging.
Single source of truth for Healer Nexus settings.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any

# ── Paths & env ─────────────────────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
os.makedirs(BASE_DIR / "logs", exist_ok=True)


# ── Settings ─────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    """Central application settings. Pydantic v2 syntax."""

    PROJECT_ID: str = "healer_nexus"
    PROJECT_NAME: str = "Healer Nexus"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    GEMINI_API_KEY: str = ""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/healer_nexus"

    TELEGRAM_BOT_TOKEN: str = ""
    ADMIN_CHAT_ID: str = ""
    API_BASE_URL: str = "http://localhost:8000"

    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"

    CRITICAL_CPU: int = 80
    CRITICAL_RAM: int = 90

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            v = v.strip().lower()
            if v in ("true", "1", "t", "y", "yes"):
                return True
            if v in ("false", "0", "f", "n", "no", "trues"):
                return False
        return bool(v)

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=False,
    )


settings = Settings()


# ── Structured logging ───────────────────────────────────────────────────────
class StructuredLogFilter(logging.Filter):
    """Add project_id and component to every log record."""

    def __init__(self, project_id: str) -> None:
        super().__init__()
        self.project_id = project_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.project_id = getattr(record, "project_id", self.project_id)
        record.component = getattr(record, "component", record.name)
        return True


_log_filter = StructuredLogFilter(settings.PROJECT_ID)
_log_format = (
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s "
    "- [project_id=%(project_id)s] - [module=%(component)s]"
)
_log_level = logging.DEBUG if settings.DEBUG else logging.INFO

_file_handler = RotatingFileHandler(
    str(BASE_DIR / "logs" / "healer_nexus.log"),
    maxBytes=10_000_000,
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setFormatter(logging.Formatter(_log_format))
_file_handler.addFilter(_log_filter)

_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(logging.Formatter(_log_format))
_stream_handler.addFilter(_log_filter)

logging.basicConfig(
    level=_log_level,
    format=_log_format,
    handlers=[_file_handler, _stream_handler],
    force=True,
)

_logger = logging.getLogger(__name__)


# ── Validation logging ───────────────────────────────────────────────────────
if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
    _logger.warning(
        "GEMINI_API_KEY is missing or empty; AI features may fail.",
        extra={"project_id": settings.PROJECT_ID, "component": "config"},
    )
else:
    _logger.info(
        "Configuration loaded successfully.",
        extra={"project_id": settings.PROJECT_ID, "component": "config"},
    )
