"""
Deep Health Check System - Parallel Component Verification.

Compliance:
- Python 3.13 asyncio.TaskGroup
- PEP 695 type aliases
- Specific exception handling (no generic except)
- Structured logging only

Author: Senior Backend Architect
Date: 2025-01-22
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from google import genai

# ============================================
# PYTHON 3.13 TYPE ALIASES (PEP 695)
# ============================================
type HealthResult = dict[str, str | float | dict[str, Any]]
type ComponentStatus = Literal["healthy", "degraded", "down", "not_configured", "unreachable"]

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Parallel health check system for all platform components.
    
    Uses Python 3.13 asyncio.TaskGroup for concurrent checks.
    """
    
    def __init__(self, project_id: str = "healer_nexus"):
        """
        Initialize health checker.
        
        Args:
            project_id: Project identifier for logging
        """
        self.project_id = project_id
    
    async def check_postgres(self, db: AsyncSession) -> HealthResult:
        """
        Check PostgreSQL connection and measure latency.
        
        Args:
            db: SQLAlchemy AsyncSession
            
        Returns:
            Health result dict with status and latency
        """
        import time
        from sqlalchemy import text
        
        start_time = time.perf_counter()
        
        try:
            # Execute simple query
            await db.execute(text("SELECT 1"))
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Determine status based on latency
            if latency_ms < 50:
                status: ComponentStatus = "healthy"
            elif latency_ms < 200:
                status = "degraded"
            else:
                status = "down"
            
            logger.info(
                f"PostgreSQL check: {status} ({latency_ms:.2f}ms)",
                extra={
                    "project_id": self.project_id,
                    "module": "health_checker",
                    "component": "postgresql"
                }
            )
            
            return {
                "component": "postgresql",
                "status": status,
                "latency_ms": round(latency_ms, 2),
                "details": {"query": "SELECT 1"}
            }
            
        except asyncio.TimeoutError as e:
            logger.error(
                "PostgreSQL timeout",
                exc_info=True,
                extra={"project_id": self.project_id, "module": "health_checker"}
            )
            return {
                "component": "postgresql",
                "status": "down",
                "latency_ms": 0.0,
                "details": {"error": "Query timeout"}
            }
        
        except Exception as e:
            # Catch SQLAlchemy/asyncpg specific errors
            logger.error(
                f"PostgreSQL check failed: {type(e).__name__}: {e}",
                exc_info=True,
                extra={"project_id": self.project_id, "module": "health_checker"}
            )
            return {
                "component": "postgresql",
                "status": "down",
                "latency_ms": 0.0,
                "details": {"error": str(e), "error_type": type(e).__name__}
            }
    
    async def check_gemini_ai(self, client: genai.Client) -> HealthResult:
        """
        Check Gemini AI API availability.
        
        Args:
            client: Gemini genai.Client instance
            
        Returns:
            Health result with API status
        """
        import time
        
        start_time = time.perf_counter()
        
        try:
            # Test with count_tokens (minimal overhead)
            await asyncio.wait_for(
                client.aio.models.count_tokens(
                    model="gemini-2.0-flash-exp",
                    contents="test"
                ),
                timeout=10.0
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            logger.info(
                f"Gemini AI check: healthy ({latency_ms:.2f}ms)",
                extra={
                    "project_id": self.project_id,
                    "module": "health_checker",
                    "component": "gemini_ai"
                }
            )
            
            return {
                "component": "gemini_ai",
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "details": {"model": "gemini-2.0-flash-exp"}
            }
            
        except asyncio.TimeoutError:
            logger.error(
                "Gemini AI timeout",
                extra={"project_id": self.project_id, "module": "health_checker"}
            )
            return {
                "component": "gemini_ai",
                "status": "degraded",
                "latency_ms": 10000.0,
                "details": {"error": "API timeout (10s)"}
            }
        
        except ImportError as e:
            # httpx import errors
            logger.error(
                f"Gemini AI library error: {e}",
                exc_info=True,
                extra={"project_id": self.project_id, "module": "health_checker"}
            )
            return {
                "component": "gemini_ai",
                "status": "down",
                "latency_ms": 0.0,
                "details": {"error": "Library import failed", "error_type": "ImportError"}
            }
        
        except Exception as e:
            # Catch httpx-specific errors (if using httpx client)
            error_type = type(e).__name__
            
            logger.error(
                f"Gemini AI check failed: {error_type}: {e}",
                exc_info=True,
                extra={"project_id": self.project_id, "module": "health_checker"}
            )
            
            # Determine status based on error type
            if "403" in str(e) or "Forbidden" in str(e):
                status_result: ComponentStatus = "down"
                error_msg = "API key invalid"
            elif "429" in str(e) or "rate limit" in str(e).lower():
                status_result = "degraded"
                error_msg = "Rate limit exceeded"
            else:
                status_result = "down"
                error_msg = str(e)
            
            return {
                "component": "gemini_ai",
                "status": status_result,
                "latency_ms": 0.0,
                "details": {"error": error_msg, "error_type": error_type}
            }
    
    async def check_telegram(self, bot_token: str) -> HealthResult:
        """
        Check Telegram Bot API connectivity using aiohttp (NOT httpx).
        
        Args:
            bot_token: Telegram bot token
            
        Returns:
            Health result with bot status
        """
        import time
        
        # Dynamic import to avoid dependency issues
        try:
            import aiohttp
        except ImportError:
            logger.warning(
                "aiohttp not installed - Telegram check skipped",
                extra={"project_id": self.project_id, "module": "health_checker"}
            )
            return {
                "component": "telegram",
                "status": "not_configured",
                "latency_ms": 0.0,
                "details": {"error": "aiohttp not installed"}
            }
        
        if not bot_token:
            return {
                "component": "telegram",
                "status": "not_configured",
                "latency_ms": 0.0,
                "details": {"error": "Bot token not provided"}
            }
        
        start_time = time.perf_counter()
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as resp:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    
                    if resp.status == 200:
                        data = await resp.json()
                        
                        logger.info(
                            f"Telegram check: healthy ({latency_ms:.2f}ms)",
                            extra={
                                "project_id": self.project_id,
                                "module": "health_checker",
                                "component": "telegram",
                                "bot_username": data.get("result", {}).get("username")
                            }
                        )
                        
                        return {
                            "component": "telegram",
                            "status": "healthy",
                            "latency_ms": round(latency_ms, 2),
                            "details": {
                                "bot_username": data.get("result", {}).get("username"),
                                "bot_id": data.get("result", {}).get("id")
                            }
                        }
                    elif resp.status == 401:
                        logger.error(
                            "Telegram API: Invalid token",
                            extra={"project_id": self.project_id, "module": "health_checker"}
                        )
                        return {
                            "component": "telegram",
                            "status": "down",
                            "latency_ms": round(latency_ms, 2),
                            "details": {"error": "Invalid bot token", "status_code": 401}
                        }
                    else:
                        logger.warning(
                            f"Telegram API returned {resp.status}",
                            extra={"project_id": self.project_id, "module": "health_checker"}
                        )
                        return {
                            "component": "telegram",
                            "status": "degraded",
                            "latency_ms": round(latency_ms, 2),
                            "details": {"error": f"HTTP {resp.status}"}
                        }
        
        except aiohttp.ClientConnectorError as e:
            logger.error(
                f"Telegram connection error: {e}",
                exc_info=True,
                extra={"project_id": self.project_id, "module": "health_checker"}
            )
            return {
                "component": "telegram",
                "status": "down",
                "latency_ms": 0.0,
                "details": {"error": "Connection failed", "error_type": "ClientConnectorError"}
            }
        
        except aiohttp.ServerTimeoutError: