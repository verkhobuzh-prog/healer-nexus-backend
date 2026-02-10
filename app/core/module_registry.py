"""
Multi-project registry: child projects visible to Admin (e.g. healer_nexus, eco-pulse).
Modular Monolith: one codebase, multiple projects via PROJECT_ID + register_child_project.
"""
from __future__ import annotations

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """Registry for this instance + child project IDs (for Admin / health)."""

    def __init__(self, project_id: str = "healer_nexus") -> None:
        self.global_project_id = project_id
        self.child_project_ids: List[str] = []

    def register_child_project(self, project_id: str) -> None:
        """Register a child project (e.g. eco-pulse) for multi-project visibility."""
        if project_id not in self.child_project_ids:
            self.child_project_ids.append(project_id)
            logger.info("📦 Registered child project: %s", project_id)

    def get_child_project_ids(self) -> List[str]:
        return list(self.child_project_ids)

    def get_all_project_ids(self) -> List[str]:
        """Current project + all registered child projects."""
        return [self.global_project_id] + self.child_project_ids


_registry: ModuleRegistry | None = None


def get_registry(project_id: str | None = None) -> ModuleRegistry:
    global _registry
    if _registry is None:
        from app.config import settings
        _registry = ModuleRegistry(project_id=project_id or getattr(settings, "PROJECT_ID", "healer_nexus"))
    return _registry
