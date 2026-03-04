"""Dashboard and auth pages (HTML)."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Pages"])

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# @router.get("/login", response_class=HTMLResponse)
# async def login_page(request: Request):
#     return templates.TemplateResponse("auth/login.html", {"request": request})


# @router.get("/register", response_class=HTMLResponse)
# async def register_page(request: Request):
#     return templates.TemplateResponse("auth/register.html", {"request": request})


# GET /dashboard removed — use /admin-dashboard or /specialist-dashboard
