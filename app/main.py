import logging
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import init_db
from app.database.seed import seed_database
from app.api.chat import router as chat_router
from app.api.specialists import router as specialists_router
from app.api.content import router as content_router
from app.api.admin_brain import router as admin_brain_router
from app.api.dashboard import router as dashboard_router
from app.api.blog_router import router as blog_router
from app.api.blog_taxonomy_router import router as blog_taxonomy_router
from app.api.blog_pages_router import router as blog_pages_router
from app.api.blog_analytics_router import router as blog_analytics_router
from app.api.booking_router import router as booking_router
from app.api.auth_router import router as auth_router
from app.api.profile_router import router as profile_router
from app.api.recommendation_router import router as recommendation_router
from app.api.specialist_pages_router import router as specialist_pages_router
from app.api.dashboard_pages_router import router as dashboard_pages_router
from app.api.seo_router import router as seo_router
from app.services.blog_scheduler import blog_scheduler
from app.services.blog_analytics_aggregator import blog_analytics_aggregator
from app.config import settings

# 1. Налаштування логування (ЗАВЖДИ ВГОРІ)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Healer Nexus Platform",
    description="Платформа для цілителів, коучів, вчителів та дизайнерів",
    version="1.0.0"
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.on_event("startup")
async def startup():
    # Важливо: цей код має бути з відступом (4 пробіли)
    await init_db()
    await seed_database()
    if settings.GEMINI_API_KEY:
        logger.info(f"✅ Gemini Key loaded: {settings.GEMINI_API_KEY[:5]}***")
    else:
        logger.error("❌ GEMINI_API_KEY IS MISSING!")
    logger.info("✅ База даних готова та синхронізована")
    await blog_scheduler.start()
    await blog_analytics_aggregator.start()


@app.on_event("shutdown")
async def shutdown():
    await blog_analytics_aggregator.stop()
    await blog_scheduler.stop()

# 2. Реєстрація API маршрутів
app.include_router(chat_router, prefix="/api")
app.include_router(specialists_router, prefix="/api")
app.include_router(content_router, prefix="/api")
app.include_router(admin_brain_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api/dashboard")
app.include_router(blog_router)
app.include_router(blog_taxonomy_router)
app.include_router(blog_pages_router)
app.include_router(blog_analytics_router)
app.include_router(booking_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(recommendation_router)
app.include_router(specialist_pages_router)
app.include_router(dashboard_pages_router)
app.include_router(seo_router)

# 3. Ендпоінти здоров'я та статики
@app.get("/api/health")
async def health():
    return {"status": "ok", "platform": "Healer Nexus"}

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("app/static/index.html")

@app.get("/tracker", include_in_schema=False)
async def tracker():
    return FileResponse("app/static/tracker.html")

@app.get("/admin", include_in_schema=False)
async def admin():
    return FileResponse("app/static/admin.html")


@app.get("/api/debug/db")
async def debug_db():
    """Тимчасовий діагностичний ендпоінт — видалити після дебагу"""
    import traceback
    from app.database.connection import async_session_maker
    from sqlalchemy import text

    results = {}

    try:
        async with async_session_maker() as session:
            # 1. Перевірка підключення
            r = await session.execute(text("SELECT 1"))
            results["connection"] = "ok"

            # 2. Список таблиць
            r = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
            tables = [row[0] for row in r.fetchall()]
            results["tables"] = tables
            results["tables_count"] = len(tables)

            # 3. Кількість спеціалістів
            try:
                r = await session.execute(text("SELECT COUNT(*) FROM specialists"))
                results["specialists_count"] = r.scalar()
            except Exception as e:
                results["specialists_error"] = str(e)

            # 4. Кількість юзерів
            try:
                r = await session.execute(text("SELECT COUNT(*) FROM users"))
                results["users_count"] = r.scalar()
            except Exception as e:
                results["users_error"] = str(e)

            # 5. Колонки таблиці specialists
            try:
                r = await session.execute(text("PRAGMA table_info(specialists)"))
                cols = [{"name": row[1], "type": row[2]} for row in r.fetchall()]
                results["specialists_columns"] = cols
            except Exception as e:
                results["specialists_columns_error"] = str(e)

            # 6. Колонки таблиці blog_posts
            try:
                r = await session.execute(text("PRAGMA table_info(blog_posts)"))
                cols = [{"name": row[1], "type": row[2]} for row in r.fetchall()]
                results["blog_posts_columns"] = cols
            except Exception as e:
                results["blog_posts_columns_error"] = str(e)

            # 7. Колонки таблиці users
            try:
                r = await session.execute(text("PRAGMA table_info(users)"))
                cols = [{"name": row[1], "type": row[2]} for row in r.fetchall()]
                results["users_columns"] = cols
            except Exception as e:
                results["users_columns_error"] = str(e)

    except Exception as e:
        results["connection_error"] = str(e)
        results["traceback"] = traceback.format_exc()

    return results


# Монтування статики
app.mount("/static", StaticFiles(directory="app/static"), name="static")