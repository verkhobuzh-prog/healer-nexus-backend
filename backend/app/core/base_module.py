"""Base module for Registry: health_check contract and safe_health_check for /api/health/full."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ModuleStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class BaseModule(ABC):
    """Module that can be registered and health-checked (e.g. can SpecialistsModule query DB?)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.status = ModuleStatus.HEALTHY
        self.last_check: Optional[datetime] = None
        self.error_count = 0
        logger.info("✅ Module '%s' initialized", name)

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Run module-level health check (e.g. query DB). Called by safe_health_check.
        Return dict must include "status": "healthy" | "degraded" | "down".
        """
        ...

    async def get_metrics(self) -> Dict[str, Any]:
        return {
            "module": self.name,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "error_count": self.error_count
        }
    
    def mark_healthy(self) -> None:
        self.status = ModuleStatus.HEALTHY
        self.last_check = datetime.now()
        self.error_count = 0

    def mark_down(self, error: Exception) -> None:
        self.status = ModuleStatus.DOWN
        self.last_check = datetime.now()
        self.error_count += 1
        logger.error("🔴 Module '%s' down: %s", self.name, error)

    async def safe_health_check(self) -> Dict[str, Any]:
        """
        Run health_check; on success mark healthy and return result.
        On exception mark down and return {"status": "down", "error": ..., "timestamp": ...}.
        Used by ModuleRegistry.get_overall_status() and /api/health/full.
        """
        try:
            result = await self.health_check()
            self.mark_healthy()
            return result
        except Exception as e:
            self.mark_down(e)
            return {"status": "down", "error": str(e), "timestamp": datetime.now().isoformat()}
