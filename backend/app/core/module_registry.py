from typing import Dict, Any, List, Optional
import asyncio
import logging
from app.core.base_module import BaseModule

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    Registry for this project's modules. Can act as "parent" for multi-project
    Admin Agent: register child projects for shared visibility (same DB or event bus).
    """
    def __init__(self, project_id: str = "healer_nexus"):
        self.modules: Dict[str, BaseModule] = {}
        self.event_bus: Any = None
        self.global_project_id: str = project_id
        # Child project IDs → their status (fetched via shared DB or event bus)
        self.child_project_ids: List[str] = []

    def register(self, module: BaseModule) -> None:
        self.modules[module.name] = module
        logger.info(f"📦 Registered module: {module.name}")

    def register_all(self) -> None:
        """Register default platform modules (e.g. SpecialistsModule)."""
        from app.modules.specialists_module import SpecialistsModule
        self.register(SpecialistsModule())

    def register_child_project(self, project_id: str) -> None:
        """Register a child project ID for Admin Agent multi-project view."""
        if project_id not in self.child_project_ids:
            self.child_project_ids.append(project_id)
            logger.info("📦 Registered child project: %s", project_id)

    def get_child_project_ids(self) -> List[str]:
        """Return IDs of child projects (for Central Admin-Agent)."""
        return list(self.child_project_ids)

    # --- ДОДАНО ВІД КЛОДА ---
    async def init_event_bus(self) -> None:
        """Initialize EventBus for this registry."""
        try:
            from app.core.event_bus import get_event_bus
            
            self.event_bus = await get_event_bus(
                project_id=self.global_project_id
            )
            
            await self.event_bus.connect()
            # Запускаємо прослуховування фоном
            asyncio.create_task(self.event_bus.listen())
            
            logger.info("✅ EventBus initialized in ModuleRegistry")
        except Exception as e:
            logger.error(f"❌ Failed to init EventBus: {e}")
    # ------------------------

    async def get_overall_status(self) -> Dict[str, Any]:
        """Run safe_health_check for all modules; return overall + per-module results for /api/health/full."""
        if not self.modules:
            return {"status": "empty", "modules": {}, "summary": {"total": 0, "healthy": 0}}

        tasks = {name: mod.safe_health_check() for name, mod in self.modules.items()}
        results = await asyncio.gather(*tasks.values())
        health_checks = dict(zip(tasks.keys(), results))

        statuses = [c.get("status", "down") for c in health_checks.values()]
        if "down" in statuses:
            overall = "down"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "overall": overall,
            "modules": health_checks,
            "summary": {"total": len(statuses), "healthy": statuses.count("healthy")},
        }

    async def get_all_metrics(self) -> Dict[str, Any]:
        return {name: await mod.get_metrics() for name, mod in self.modules.items()}

    async def get_all_projects_status(self) -> Dict[str, Any]:
        """
        For Central Admin-Agent: this project + child projects status.
        Children can be filled via Shared DB or EventBus later.
        """
        this_status = await self.get_overall_status()
        result: Dict[str, Any] = {
            "this_project_id": self.global_project_id,
            "this": this_status,
            "children": {},
        }
        for pid in self.child_project_ids:
            # Placeholder: real impl would query shared DB or event bus
            result["children"][pid] = {"status": "unknown", "source": "placeholder"}
        return result


_registry: ModuleRegistry = ModuleRegistry()


def get_registry() -> ModuleRegistry:
    return _registry