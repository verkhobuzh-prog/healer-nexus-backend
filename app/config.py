import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Визначаємо базову директорію та завантажуємо .env
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings(BaseSettings):
    """Multi-project: one codebase, PROJECT_ID per instance (e.g. healer_nexus, eco-pulse)."""
    PROJECT_ID: str = "healer_nexus"
    GEMINI_API_KEY: str
    DATABASE_URL: str = "sqlite+aiosqlite:///./healer.db?charset=utf8"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_PROXY: str = ""  # e.g. socks5://user:pass@host:port or socks5://127.0.0.1:1080
    HEALER_SPECIALIST_BOT_TOKEN: str = ""
    HEALER_CONSUMER_BOT_TOKEN: str = ""
    ADMIN_CHAT_ID: str = ""
    BASE_URL: str = Field(default="http://localhost:8000", env="BASE_URL")
    DEBUG: bool = False
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Валідація при старті
if not settings.GEMINI_API_KEY:
    print("❌ ПОМИЛКА: GEMINI_API_KEY не знайдено в .env")
else:
    print(f"✅ Конфіг завантажено. Ключ починається на: {settings.GEMINI_API_KEY[:5]}...")
