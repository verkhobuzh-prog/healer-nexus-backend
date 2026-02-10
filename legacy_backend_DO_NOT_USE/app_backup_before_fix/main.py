import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Імпорт внутрішніх модулів
from app.database.connection import init_db
from app.api.chat import router as chat_router
from app.api.specialists import router as specialists_router
from app.api.services import router as services_router
from app.api.health import router as health_router  # Явний імпорт

# Модульна архітектура
from app.core.module_registry import get_registry
from app.modules.specialists_module import SpecialistsModule
from app.services.simple_analytics import analytics

# Логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: startup / shutdown"""
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info("🚀 Starting Healer Nexus Platform...")

    await init_db()
    logger.info("✅ Database initialized")

    # Реєстрація модулів
    registry = get_registry()
    registry.register(SpecialistsModule())
    logger.info("✅ Modules registered")

    # Початкова перевірка
    status = await registry.get_overall_status()
    logger.info(f"📊 Initial system status: {status['overall']}")

    # Очистка аналітики
    analytics.clear_old_data(days=30)
    logger.info("🧹 Analytics cleaned")

    yield

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("🛑 Shutting down...")


app = FastAPI(
    title="Healer Nexus Platform",
    description="Hybrid AI-Human marketplace for healers, coaches, teachers & creatives",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API ROUTERS ───────────────────────────────────────────────────────────────
app.include_router(chat_router,        prefix="/api", tags=["Chat"])
app.include_router(specialists_router, prefix="/api", tags=["Specialists"])
app.include_router(services_router,    prefix="/api", tags=["Services"])
app.include_router(health_router,      prefix="/api", tags=["System"])


# ── STATIC PAGES ──────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("app/static/index.html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    return FileResponse("app/static/dashboard.html")


# ── STATIC FILES ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
