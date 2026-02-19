import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import init_db
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Важливо: цей код має бути з відступом (4 пробіли)
    await init_db()
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

# 3. Ендпоінти здоров'я та статики
@app.get("/api/health")
async def health():
    return {"status": "ok", "platform": "Healer Nexus"}

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("app/static/index.html")

@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    return FileResponse("app/static/dashboard.html")

@app.get("/tracker", include_in_schema=False)
async def tracker():
    return FileResponse("app/static/tracker.html")

@app.get("/admin", include_in_schema=False)
async def admin():
    return FileResponse("app/static/admin.html")

# Монтування статики
app.mount("/static", StaticFiles(directory="app/static"), name="static")