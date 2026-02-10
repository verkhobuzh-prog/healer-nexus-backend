from typing import Dict, Any, List
import asyncio
import logging
from app.core.base_module import BaseModule

logger = logging.getLogger(__name__)

class ModuleRegistry:
    def __init__(self):
        self.modules: Dict[str, BaseModule] = {}
    
    def register(self, module: BaseModule):
        self.modules[module.name] = module
        logger.info(f"📦 Registered module: {module.name}")
    
    async def get_overall_status(self) -> Dict[str, Any]:
        tasks = {name: mod.safe_health_check() for name, mod in self.modules.items()}
        results = await asyncio.gather(*tasks.values())
        health_checks = dict(zip(tasks.keys(), results))
        
        statuses = [c.get("status", "down") for c in health_checks.values()]
        overall = "healthy" if "down" not in statuses else "down"
        
        return {
            "overall": overall,
            "modules": health_checks,
            "summary": {"total": len(statuses), "healthy": statuses.count("healthy")}
        }

    async def get_all_metrics(self) -> Dict[str, Any]:
        return {name: await mod.get_metrics() for name, mod in self.modules.items()}

_registry = ModuleRegistry()
def get_registry() -> ModuleRegistry: return _registry
