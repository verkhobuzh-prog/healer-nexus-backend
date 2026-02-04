import asyncio
import logging
from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database.connection import init_db
from app.api.chat import router as chat_router
from app.api.specialists import router as specialists_router
from app.api.services import router as services_router
from app.api.health import router as health_router
from app.telegram.bot_runner import start_bot_process

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


async def _metrics_collector() -> None:
    """Background task: collect system metrics every 60 seconds."""
    from app.automation.monitoring import collect_system_metrics
    while True:
        try:
            await collect_system_metrics()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Metrics collection failed: %s", e, exc_info=True)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Healer Nexus Platform", extra={"project_id": settings.PROJECT_ID})

    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # Activate modules (Registry) and EventBus stub
    from app.core.module_registry import get_registry
    registry = get_registry()
    registry.register_all()
    await registry.init_event_bus()
    logger.info("✅ Modules and EventBus initialized")

    # Start Telegram bot (healer_bot in background thread)
    bot_thread = start_bot_process()
    app.state.bot_thread = bot_thread
    logger.info("✅ Telegram Healer bot started")

    # Start metrics collector
    metrics_task = asyncio.create_task(_metrics_collector())
    app.state.metrics_task = metrics_task
    logger.info("✅ System metrics collector started")

    logger.info("🎉 Platform ready (SQLite + EventBus stub)")

    yield

    # === SHUTDOWN ===
    logger.info("🛑 Shutting down gracefully")

    # Stop metrics collector
    if hasattr(app.state, "metrics_task") and app.state.metrics_task is not None:
        app.state.metrics_task.cancel()
        try:
            await app.state.metrics_task
        except asyncio.CancelledError:
            pass
        app.state.metrics_task = None
        logger.info("System metrics collector stopped")

    # Disconnect EventBus stub
    from app.core.module_registry import get_registry
    registry = get_registry()
    if getattr(registry, "event_bus", None) is not None:
        try:
            await registry.event_bus.disconnect()
        except Exception as e:
            logger.warning("EventBus disconnect: %s", e)

    # Bot thread is daemon - will auto-stop
    if hasattr(app.state, "bot_thread") and app.state.bot_thread is not None:
        app.state.bot_thread = None

    logger.info("✅ Shutdown complete")


app = FastAPI(
    title="Healer Nexus Platform",
    description="AI-Powered Multi-Project Orchestration Platform",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(specialists_router, prefix="/api", tags=["Specialists"])
app.include_router(services_router, prefix="/api", tags=["Services"])
app.include_router(health_router, prefix="/api", tags=["Health"])


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/admin", include_in_schema=False)
async def admin():
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/tracker", include_in_schema=False)
async def tracker():
    return FileResponse(STATIC_DIR / "tracker.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
