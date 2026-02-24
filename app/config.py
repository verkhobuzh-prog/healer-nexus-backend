import os
import sys
import logging
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Визначаємо базову директорію та завантажуємо .env
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Multi-project: one codebase, PROJECT_ID per instance (e.g. healer_nexus, eco-pulse)."""
    PROJECT_ID: str = "healer_nexus"
    GEMINI_API_KEY: str = ""
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./healer.db?charset=utf8",
        description="SQLite for local dev; set to PostgreSQL URL (e.g. from Render) for production.",
    )
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_PROXY: str = ""  # e.g. socks5://user:pass@host:port or socks5://127.0.0.1:1080
    HEALER_SPECIALIST_BOT_TOKEN: str = ""
    HEALER_CONSUMER_BOT_TOKEN: str = ""
    ADMIN_CHAT_ID: str = ""
    BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Public base URL; set via BASE_URL env (e.g. https://yourapp.onrender.com).",
    )
    DEBUG: bool = False
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

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    if os.getenv("ENVIRONMENT", "development") == "production":
        print("FATAL: JWT_SECRET_KEY not set!", file=sys.stderr)
        sys.exit(1)
    else:
        import secrets
        JWT_SECRET_KEY = secrets.token_hex(32)
        print("WARNING: JWT_SECRET_KEY not set, using random key (dev only)")
settings.JWT_SECRET_KEY = JWT_SECRET_KEY

# GEMINI_API_KEY: if missing, AI features are disabled; app does not crash
if not settings.GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not set - AI features disabled")
else:
    logger.info("GEMINI_API_KEY is set")
