from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ModuleStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"

class BaseModule(ABC):
    def __init__(self, name: str):
        self.name = name
        self.status = ModuleStatus.HEALTHY
        self.last_check: Optional[datetime] = None
        self.error_count = 0
        logger.info(f"✅ Module '{name}' initialized")
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass
    
    async def get_metrics(self) -> Dict[str, Any]:
        return {
            "module": self.name,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "error_count": self.error_count
        }
    
    def mark_healthy(self):
        self.status = ModuleStatus.HEALTHY
        self.last_check = datetime.now()
        self.error_count = 0

    def mark_down(self, error: Exception):
        self.status = ModuleStatus.DOWN
        self.last_check = datetime.now()
        self.error_count += 1
        logger.error(f"🔴 Module '{self.name}' down: {error}")

    async def safe_health_check(self) -> Dict[str, Any]:
        try:
            result = await self.health_check()
            self.mark_healthy()
            return result
        except Exception as e:
            self.mark_down(e)
            return {"status": "down", "error": str(e), "timestamp": datetime.now().isoformat()}
