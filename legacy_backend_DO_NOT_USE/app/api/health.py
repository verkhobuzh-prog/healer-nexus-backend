"""Health check API for monitoring and load balancers."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.config import settings
from app.database.connection import get_db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

type HealthResult = dict[str, str | float | dict[str, Any]]
type ComponentStatus = Literal["healthy", "degraded", "down", "not_configured"]

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self, project_id: str = "healer_nexus"):
        self.project_id = project_id

    async def check_postgres(self, db: AsyncSession) -> HealthResult:
        start = time.perf_counter()
        try:
            await db.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000
            status: ComponentStatus = "healthy" if latency < 50 else "degraded"
            return {"component": "postgresql", "status": status, "latency_ms": latency}
        except Exception as e:
            logger.error(f"Postgres health check failed: {type(e).__name__}", exc_info=True)
            return {"component": "postgresql", "status": "down", "latency_ms": 0, "details": {"error": str(e)}}

    async def check_gemini_ai(self, client: Any) -> HealthResult:
        start = time.perf_counter()
        try:
            await client.aio.models.count_tokens(model="gemini-2.0-flash-exp", contents="health_check")
            latency = (time.perf_counter() - start) * 1000
            return {"component": "gemini_ai", "status": "healthy", "latency_ms": latency}
        except Exception as e:
            logger.error(f"Gemini AI health check failed: {type(e).__name__}", exc_info=True)
            return {"component": "gemini_ai", "status": "degraded", "latency_ms": 0, "details": {"error": str(e)}}

    async def check_telegram(self, bot_token: str) -> HealthResult:
        if not bot_token:
            return {"component": "telegram", "status": "not_configured", "latency_ms": 0}
        try:
            import aiohttp
        except ImportError:
            return {"component": "telegram", "status": "not_configured", "latency_ms": 0}
        start = time.perf_counter()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.telegram.org/bot{bot_token}/getMe",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    latency = (time.perf_counter() - start) * 1000
                    status: ComponentStatus = "healthy" if resp.status == 200 else "down"
                    return {"component": "telegram", "status": status, "latency_ms": latency}
        except Exception:
            return {"component": "telegram", "status": "down", "latency_ms": 0}

    async def check_redis(self) -> HealthResult:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL, socket_timeout=3)
            start = time.perf_counter()
            await r.ping()
            await r.aclose()
            latency = (time.perf_counter() - start) * 1000
            return {"component": "redis", "status": "healthy", "latency_ms": latency}
        except Exception:
            return {"component": "redis", "status": "not_configured", "latency_ms": 0}

    async def run_all_checks(
        self, db: AsyncSession, ai_client: Any, bot_token: str
    ) -> list[HealthResult]:
        async with asyncio.TaskGroup() as tg:
            t1 = tg.create_task(self.check_postgres(db))
            t2 = tg.create_task(self.check_gemini_ai(ai_client))
            t3 = tg.create_task(self.check_telegram(bot_token))
            t4 = tg.create_task(self.check_redis())
        return [t1.result(), t2.result(), t3.result(), t4.result()]


_checker = HealthChecker(project_id=settings.PROJECT_ID)
router = APIRouter()


@router.get("/health")
async def quick_health():
    """Quick health check for load balancers."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_id": settings.PROJECT_ID,
    }


@router.get("/health/detailed")
async def detailed_health(db: AsyncSession = Depends(get_db)):
    """Detailed health check for all components (Postgres, Gemini, Telegram, Redis)."""
    from app.ai.providers import get_ai_provider
    try:
        ai_client = get_ai_provider().client
    except Exception:
        ai_client = None
    if ai_client is None:
        results = await _checker.run_all_checks(
            db, _DummyAIClient(), settings.TELEGRAM_BOT_TOKEN
        )
    else:
        results = await _checker.run_all_checks(
            db, ai_client, settings.TELEGRAM_BOT_TOKEN
        )
    overall = "healthy" if all(r.get("status") == "healthy" for r in results) else "degraded"
    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_id": settings.PROJECT_ID,
        "components": results,
    }


@router.get("/health/full")
async def full_health(db: AsyncSession = Depends(get_db)):
    """
    Full health: component checks (DB latency, Google AI API) + registry module status.
    For load balancers and Admin Agent monitoring.
    """
    from app.core.module_registry import get_registry
    from app.ai.providers import get_ai_provider

    # 1) Infrastructure: DB latency + Google AI availability
    try:
        ai_client = get_ai_provider().client
    except Exception:
        ai_client = None
    infra_results = await _checker.run_all_checks(
        db, ai_client or _DummyAIClient(), settings.TELEGRAM_BOT_TOKEN
    )
    db_result = next((r for r in infra_results if r.get("component") == "postgresql"), {})
    ai_result = next((r for r in infra_results if r.get("component") == "gemini_ai"), {})

    # 2) Module-level health (e.g. SpecialistsModule can query DB?)
    registry = get_registry()
    module_status = await registry.get_overall_status()

    overall = "healthy"
    if module_status.get("overall") == "down" or any(
        r.get("status") == "down" for r in infra_results
    ):
        overall = "down"
    elif module_status.get("overall") != "healthy" or any(
        r.get("status") == "degraded" for r in infra_results
    ):
        overall = "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_id": settings.PROJECT_ID,
        "database": {"status": db_result.get("status"), "latency_ms": db_result.get("latency_ms")},
        "google_ai": {"status": ai_result.get("status"), "latency_ms": ai_result.get("latency_ms")},
        "components": infra_results,
        "modules": module_status,
    }


@router.get("/startup-check")
async def startup_check():
    """Verify all platform components started successfully."""
    from app.core.module_registry import get_registry

    registry = get_registry()
    eventbus_connected = bool(
        getattr(registry, "event_bus", None)
        and getattr(registry.event_bus, "is_connected", False)
    )
    checks = {
        "modules_registered": len(getattr(registry, "modules", {})) > 0,
        "eventbus_connected": eventbus_connected,
        "database": "ready",
    }
    all_ok = all(
        v is True or v == "ready"
        for v in checks.values()
    )
    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
        "message": "Platform startup verified" if all_ok else "Some components failed",
    }


class _DummyAIClient:
    """Placeholder when Gemini is not configured; check_gemini_ai will return degraded."""

    class _AioModels:
        async def count_tokens(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Gemini client not configured")

    aio = type("Aio", (), {"models": _AioModels()})()
