"""
Self-healing: automatic restart of internal services on AssertionError (Python 3.13).
Use for AI client, DB pool, or bot lifecycle — register callbacks and wrap critical calls.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Callbacks invoked on AssertionError: async () -> None (e.g. re-init client)
_restart_handlers: list[Callable[[], Awaitable[None]]] = []


def register_restart_handler(handler: Callable[[], Awaitable[None]]) -> None:
    """Register a callback to run when AssertionError triggers self-heal."""
    _restart_handlers.append(handler)


async def run_restart_handlers() -> None:
    """Run all registered restart handlers (e.g. after AssertionError)."""
    for h in _restart_handlers:
        try:
            await h()
        except Exception as e:
            logger.error("Restart handler failed: %s", e, exc_info=True)


async def with_self_heal(
    coro: Awaitable[T],
    *,
    on_assertion: bool = True,
) -> T:
    """
    Execute coroutine; on AssertionError run restart handlers and re-raise.
    Python 3.13: AssertionError is unchanged; use for internal invariants.
    """
    try:
        return await coro
    except AssertionError as e:
        logger.warning("AssertionError in critical path, running restart handlers: %s", e)
        await run_restart_handlers()
        raise
