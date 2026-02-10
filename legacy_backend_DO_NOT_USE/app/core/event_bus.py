"""EventBus stub for SQLite deployment (no LISTEN/NOTIFY support).
For real-time events, upgrade to Redis Pub/Sub or use polling."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class EventBus:
    """Stub EventBus for SQLite - stores handlers but doesn't dispatch.
    Upgrade to Redis/PostgreSQL for real pub/sub."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self._handlers: dict[str, list[Callable[[dict], Awaitable[None]]]] = {}
        self._connected = False

    async def connect(self) -> None:
        """Stub connect - no actual connection needed for SQLite."""
        self._connected = True
        logger.info(
            "✅ EventBus stub connected (project: %s) - no real pub/sub",
            self.project_id,
        )

    async def disconnect(self) -> None:
        """Stub disconnect."""
        self._connected = False
        logger.info("EventBus stub disconnected")

    async def listen(self) -> None:
        """Stub listen - no-op loop so registry's create_task(listen()) doesn't exit.
        SQLite has no LISTEN/NOTIFY; use Redis for real subscription."""
        while self._connected:
            await asyncio.sleep(3600)

    async def emit(self, channel: str, payload: dict) -> None:
        """Stub emit - logs event but doesn't broadcast.
        Upgrade to Redis for real broadcasting."""
        logger.debug("📤 Event emitted (stub): %s → %s", channel, payload)

    def subscribe(
        self,
        channel: str,
        handler: Callable[[dict], Awaitable[None]],
    ) -> None:
        """Register handler for channel (stub - won't receive events from other processes)."""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)
        logger.debug("📥 Subscribed to channel (stub): %s", channel)

    @property
    def is_connected(self) -> bool:
        """Check if stub is 'connected'."""
        return self._connected


async def get_event_bus(project_id: str) -> EventBus:
    """Return EventBus stub for the given project."""
    return EventBus(project_id)


async def init_event_bus() -> None:
    """Stub entry point; no-op (registry calls get_event_bus + connect + listen)."""
    pass
