import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Визначаємо базову директорію та завантажуємо .env
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    DATABASE_URL: str = "sqlite+aiosqlite:///./healer.db"
    TELEGRAM_BOT_TOKEN: str = ""
    ADMIN_CHAT_ID: str = ""
    DEBUG: bool = False
    
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
