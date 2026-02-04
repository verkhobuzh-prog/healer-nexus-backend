"""
Backward compatibility: re-export settings from app.config.
Prefer: from app.config import settings
"""
from app.config import settings

__all__ = ["settings"]
