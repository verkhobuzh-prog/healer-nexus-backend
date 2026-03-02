"""
Healer Nexus — Configuration
Fixed: Added GEMINI_ENABLED flag, CLOUD_SQL_CONNECTION_NAME, cleaned up JWT handling
"""

import os
import sys
import logging
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Base directory & .env
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Multi-project: one codebase, PROJECT_ID per instance."""

    PROJECT_ID: str = "healer_nexus"
    ENVIRONMENT: str = "development"

    # AI
    GEMINI_API_KEY: str = ""
    GEMINI_ENABLED: bool = True  # Toggle AI features without redeploy

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./healer_nexus.db",
        description="SQLite for local dev; PostgreSQL URL for production.",
    )
    CLOUD_SQL_CONNECTION_NAME: str = ""  # e.g. project:region:instance

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_PROXY: str = ""
    HEALER_SPECIALIST_BOT_TOKEN: str = ""
    HEALER_CONSUMER_BOT_TOKEN: str = ""
    ADMIN_CHAT_ID: str = ""

    # URLs
    BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Public base URL for links in Telegram posts etc.",
    )
    DEBUG: bool = False

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # JWT
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# --- JWT_SECRET_KEY: require in production, auto-generate in dev ---
if not settings.JWT_SECRET_KEY:
    if settings.ENVIRONMENT == "production":
        print("FATAL: JWT_SECRET_KEY not set in production!", file=sys.stderr)
        sys.exit(1)
    else:
        import secrets
        settings.JWT_SECRET_KEY = secrets.token_hex(32)
        print("WARNING: JWT_SECRET_KEY not set, using random key (dev only)")

# --- Gemini status ---
if not settings.GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not set — AI features disabled")
    settings.GEMINI_ENABLED = False
elif not settings.GEMINI_ENABLED:
    logger.info("GEMINI_ENABLED=false — AI features disabled by flag")
else:
    logger.info("Gemini AI enabled")