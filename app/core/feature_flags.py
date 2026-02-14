"""
Feature flags: per-project toggles for personalized AI bots.
Integrates with ModuleRegistry + project_id. EventBus can emit flag changes.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default flags per project (can be overridden by env/DB later)
_DEFAULT_FLAGS: dict[str, dict[str, Any]] = {
    "healer_nexus": {
        "personalized_bots": True,
        "emotion_analysis": True,
        "ethical_disclaimer": True,
        "empathy_80_20": True,
    },
    "eco_pulse": {
        "personalized_bots": False,
        "emotion_analysis": False,
        "ethical_disclaimer": True,
        "empathy_80_20": True,
    },
}


def get_flag(project_id: str, flag_name: str, default: Any = False) -> Any:
    """
    Get feature flag value for a project.
    Uses ModuleRegistry project list; falls back to defaults.
    """
    from app.config import settings
    from app.core.module_registry import get_registry

    registry = get_registry()
    all_ids = registry.get_all_project_ids()
    if project_id not in all_ids:
        registry.register_child_project(project_id)

    flags = _DEFAULT_FLAGS.get(project_id) or _DEFAULT_FLAGS.get(
        getattr(settings, "PROJECT_ID", "healer_nexus"), {}
    )
    return flags.get(flag_name, default)


def set_flag_local(project_id: str, flag_name: str, value: Any) -> None:
    """Set flag in-memory (for tests or runtime override). Not persisted."""
    if project_id not in _DEFAULT_FLAGS:
        _DEFAULT_FLAGS[project_id] = {}
    _DEFAULT_FLAGS[project_id][flag_name] = value
    logger.info("Feature flag set: %s.%s = %s", project_id, flag_name, value)


def get_all_flags(project_id: str) -> dict[str, Any]:
    """Return all flags for a project (merged with defaults)."""
    base = _DEFAULT_FLAGS.get("healer_nexus", {}).copy()
    base.update(_DEFAULT_FLAGS.get(project_id, {}))
    return base
