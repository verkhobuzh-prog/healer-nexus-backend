"""
Healer Nexus — Main Application
Fixed: removed debug endpoints, GEMINI_ENABLED guard on scheduler, clean startup
"""

import logging
import os

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from app.database.connection import init_db
from app.database.seed import seed_database
from app.config import settings

# Routers
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
from app.api.admin_users_router import router as admin_users_router
from app.api.profile_router import router as profile_router
from app.api.recommendation_router import router as recommendation_router
from app.api.specialist_pages_router import router as specialist_pages_router
from app.api.dashboard_pages_router import router as dashboard_pages_router
from app.api.seo_router import router as seo_router

# Background tasks
from app.services.blog_scheduler import blog_scheduler
from app.services.blog_analytics_aggregator import blog_analytics_aggregator

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- App ---
app = FastAPI(
    title="Healer Nexus Platform",
    description="Платформа для цілителів, коучів, вчителів та дизайнерів",
    version="1.0.0",
)

# --- CORS ---
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# --- Health (no auth, no debug info) ---
@app.get("/api/health")
async def health():
    return {"status": "ok", "platform": "Healer Nexus"}


# --- Startup / Shutdown ---
@app.on_event("startup")
async def startup():
    await init_db()
    await seed_database()

    # Gemini status
    if settings.GEMINI_ENABLED:
        logger.info("Gemini AI: enabled")
    else:
        logger.info("Gemini AI: disabled (GEMINI_ENABLED=false or no API key)")

    # Blog scheduler uses Gemini for auto-generation — only start if AI enabled
    if settings.GEMINI_ENABLED:
        await blog_scheduler.start()

    # Analytics aggregator doesn't need Gemini — always start
    await blog_analytics_aggregator.start()

    logger.info("Healer Nexus started")


@app.on_event("shutdown")
async def shutdown():
    await blog_analytics_aggregator.stop()
    if settings.GEMINI_ENABLED:
        await blog_scheduler.stop()


# --- API Routers ---
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
app.include_router(admin_users_router)
app.include_router(profile_router)
app.include_router(recommendation_router)
app.include_router(specialist_pages_router)
app.include_router(dashboard_pages_router)
app.include_router(seo_router)

# Templates for dashboard login
_templates_dir = Path(__file__).resolve().parent / "templates"
_templates = Jinja2Templates(directory=str(_templates_dir))


# --- Static pages ---
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("app/static/index.html")


@app.get("/tracker", include_in_schema=False)
async def tracker():
    return FileResponse("app/static/tracker.html")


@app.get("/admin", include_in_schema=False)
async def admin():
    return FileResponse("app/static/admin.html")


@app.get("/login", include_in_schema=False)
async def login_redirect():
    return RedirectResponse(url="/dashboard/login")


@app.get("/dashboard/login", include_in_schema=False)
async def login_page(request: Request):
    return _templates.TemplateResponse("dashboard/login.html", {"request": request})


@app.get("/admin-dashboard", include_in_schema=False)
async def admin_dashboard_page():
    return FileResponse("app/static/dashboard.html")


@app.get("/specialist-dashboard", include_in_schema=False)
async def specialist_dashboard_page():
    return FileResponse("app/templates/dashboard/specialist.html")


# Static files (mount AFTER all routes)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
