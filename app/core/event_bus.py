"""
PostgreSQL LISTEN/NOTIFY Event Bus for Multi-Project Orchestration.

Strict adherence to .cursorrules:
- Registry Pattern compliant
- Python 3.13 PEP 695 type aliases
- Lazy asyncpg loading (no import-time errors)
- Structured logging only (no print statements)
- Async-first architecture

Author: Senior Backend Architect
Date: 2025-01-22
Python: 3.13.11
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

# ============================================
# TYPE-CHECKING ONLY IMPORTS (IDE support)
# ============================================
if TYPE_CHECKING:
    from asyncpg import Connection, PostgresError
else:
    # Runtime: Don't import asyncpg yet (lazy loading)
    Connection = None
    PostgresError = Exception  # Fallback type for except blocks

# ============================================
# PYTHON 3.13 TYPE ALIASES (PEP 695)
# ============================================
type EventCallback = Callable[[dict[str, Any]], Any]
type EventPayload = dict[str, Any]
type HealthStatus = dict[str, str | float | dict[str, Any]]

logger = logging.getLogger(__name__)


# ============================================
# CUSTOM EXCEPTIONS
# ============================================
class EventBusError(Exception):
    """Base exception for EventBus operations."""
    pass


class EventBusConnectionError(EventBusError):
    """Raised when EventBus cannot connect to PostgreSQL."""
    pass


class EventBusNotConnectedError(EventBusError):
    """Raised when attempting operations on disconnected bus."""
    pass


# ============================================
# EVENT BUS IMPLEMENTATION
# ============================================
class EventBus:
    """
    PostgreSQL LISTEN/NOTIFY event bus for real-time orchestration.
    
    Features:
    - Lazy asyncpg loading (prevents import-time AttributeError)
    - Automatic reconnection with exponential backoff
    - Thread-safe callback registration
    - Python 3.13 ExceptionGroup handling
    - Registry Pattern compliant
    
    Payload Format:
        NOTIFY channel: "project_id:event_type:origin_module"
    
    Example:
        >>> bus = await get_event_bus("healer_nexus")
        >>> await bus.connect()
        >>> bus.register_callback("error", handle_error)
        >>> await bus.emit("healer_nexus", "test_event", "test_module")
    """
    
    # Singleton state
    _instance: EventBus | None = None
    _lock = asyncio.Lock()
    
    def __init__(
        self,
        project_id: str = "healer_nexus",
        database_url: str | None = None
    ):
        """
        Initialize EventBus (use get_event_bus() instead).
        
        Args:
            project_id: Project identifier for event emission
            database_url: PostgreSQL connection string (auto-detected if None)
        """
        # Auto-detect database URL from environment
        if database_url is None:
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost/healer_nexus"
            )
        
        self.database_url = database_url
        self.project_id = project_id
        self.running = False
        
        # Callback registry: {event_type: [callback1, callback2, ...]}
        self.callbacks: dict[str, list[EventCallback]] = defaultdict(list)
        
        # Connection state (string type hint to avoid import-time error)
        self._connection: "Connection | None" = None
        self._asyncpg_module: Any = None  # Lazy-loaded module reference
        
        # Reconnection tracking
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        
        # Rate limiting state
        self._last_emit_time: dict[str, float] = {}
        self._emit_cooldown_seconds = 1.0
        
        logger.info(
            "EventBus initialized",
            extra={
                "project_id": project_id,
                "module": "event_bus",
                "database": database_url.split("@")[-1] if "@" in database_url else "local"
            }
        )
    
    def _lazy_load_asyncpg(self) -> Any:
        """
        Lazy load asyncpg module at runtime.
        
        Returns:
            asyncpg module object
            
        Raises:
            ImportError: If asyncpg is not installed
            
        Note:
            This prevents AttributeError during module import phase.
        """
        if self._asyncpg_module is not None:
            return self._asyncpg_module
        
        try:
            import asyncpg as pg_module
            self._asyncpg_module = pg_module
            
            logger.debug(
                "asyncpg module loaded successfully",
                extra={"project_id": self.project_id, "module": "event_bus"}
            )
            
            return pg_module
            
        except ImportError as e:
            error_msg = (
                "asyncpg is required for EventBus. "
                "Install with: pip install asyncpg>=0.31.0"
            )
            logger.error(
                error_msg,
                extra={"project_id": self.project_id, "module": "event_bus"}
            )
            raise ImportError(error_msg) from e
    
    async def connect(self) -> None:
        """
        Establish PostgreSQL connection and execute LISTEN.
        
        Idempotent - safe to call multiple times.
        
        Raises:
            ImportError: If asyncpg not installed
            EventBusConnectionError: If connection fails
        """
        # Skip if already connected
        if self._connection is not None and not self._connection.is_closed():
            logger.debug(
                "EventBus already connected",
                extra={"project_id": self.project_id, "module": "event_bus"}
            )
            return
        
        # Lazy load asyncpg
        pg_module = self._lazy_load_asyncpg()
        
        try:
            # Establish connection with timeout
            self._connection = await asyncio.wait_for(
                pg_module.connect(
                    self.database_url,
                    timeout=10.0,
                    command_timeout=5.0
                ),
                timeout=15.0
            )
            
            # Execute LISTEN on orchestrator events channel
            await self._connection.execute("LISTEN orchestrator_events")
            
            self.running = True
            self._reconnect_attempts = 0
            
            logger.info(
                "EventBus connected to PostgreSQL",
                extra={
                    "project_id": self.project_id,
                    "module": "event_bus",
                    "channel": "orchestrator_events",
                    "server_version": self._connection.get_server_version()
                }
            )
            
        except asyncio.TimeoutError as e:
            error_msg = f"Connection timeout after 15s: {self.database_url}"
            logger.error(
                error_msg,
                exc_info=True,
                extra={"project_id": self.project_id, "module": "event_bus"}
            )
            raise EventBusConnectionError(error_msg) from e
        
        except Exception as e:
            # Catch asyncpg-specific errors (loaded at runtime)
            error_msg = f"Failed to connect: {type(e).__name__}: {e}"
            logger.error(
                error_msg,
                exc_info=True,
                extra={
                    "project_id": self.project_id,
                    "module": "event_bus",
                    "error_type": type(e).__name__
                }
            )
            raise EventBusConnectionError(error_msg) from e
    
    async def listen(self) -> None:
        """
        Start listening for PostgreSQL notifications (long-running).
        
        Automatically reconnects on connection loss with exponential backoff.
        Should be run as background task: asyncio.create_task(bus.listen())
        """
        # Ensure connected before listening
        if not self.running or self._connection is None:
            await self.connect()
        
        logger.info(
            "EventBus listener started",
            extra={"project_id": self.project_id, "module": "event_bus"}
        )
        
        while self.running:
            try:
                # Register notification callback
                await self._connection.add_listener(
                    "orchestrator_events",
                    self._on_notification
                )
                
                # Keep connection alive with heartbeat
                while self.running:
                    await asyncio.sleep(30)  # Heartbeat every 30s
                    
                    # Check connection health
                    if self._connection.is_closed():
                        logger.warning(
                            "Connection closed, triggering reconnect",
                            extra={"project_id": self.project_id, "module": "event_bus"}
                        )
                        raise ConnectionError("PostgreSQL connection lost")
                    
                    # Send heartbeat query
                    try:
                        await asyncio.wait_for(
                            self._connection.fetchval("SELECT 1"),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Heartbeat timeout, connection may be stale",
                            extra={"project_id": self.project_id, "module": "event_bus"}
                        )
                        raise ConnectionError("Heartbeat failed")
                
            except asyncio.CancelledError:
                logger.info(
                    "EventBus listener cancelled gracefully",
                    extra={"project_id": self.project_id, "module": "event_bus"}
                )
                break
            
            except (ConnectionError, OSError) as e:
                # Handle connection-specific errors
                logger.error(
                    f"Connection error: {type(e).__name__}: {e}",
                    exc_info=True,
                    extra={"project_id": self.project_id, "module": "event_bus"}
                )
                
                await self._attempt_reconnect()
            
            except Exception as e:
                # Catch any other asyncpg errors
                logger.error(
                    f"EventBus listener error: {type(e).__name__}: {e}",
                    exc_info=True,
                    extra={"project_id": self.project_id, "module": "event_bus"}
                )
                
                await self._attempt_reconnect()
        
        logger.info(
            "EventBus listener stopped",
            extra={"project_id": self.project_id, "module": "event_bus"}
        )
    
    async def _attempt_reconnect(self) -> None:
        """Attempt reconnection with exponential backoff."""
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            wait_time = min(5 * (2 ** self._reconnect_attempts), 300)  # Max 5 min
            
            logger.warning(
                f"Reconnecting in {wait_time}s "
                f"(attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})",
                extra={"project_id": self.project_id, "module": "event_bus"}
            )
            
            await asyncio.sleep(wait_time)
            
            try:
                await self.connect()
            except EventBusConnectionError:
                logger.error(
                    "Reconnection failed, will retry",
                    extra={"project_id": self.project_id, "module": "event_bus"}
                )
        else:
            logger.critical(
                "Max reconnection attempts reached - EventBus entering degraded mode",
                extra={"project_id": self.project_id, "module": "event_bus"}
            )
            self.running = False
    
    async def _on_notification(
        self,
        connection: Any,
        pid: int,
        channel: str,
        payload: str
    ) -> None:
        """
        Handle incoming PostgreSQL notification.
        
        Payload format: "project_id:event_type:origin_module"
        
        Args:
            connection: asyncpg Connection object
            pid: PostgreSQL backend PID
            channel: Notification channel name
            payload: Notification payload string
        """
        try:
            # Parse payload: "project_id:event_type:origin_module"
            parts = payload.split(":", 2)
            
            if len(parts) < 2:
                logger.warning(
                    f"Invalid payload format: {payload}",
                    extra={
                        "project_id": self.project_id,
                        "module": "event_bus",
                        "channel": channel
                    }
                )
                return
            
            proj_id = parts[0]
            event_type = parts[1]
            origin_module = parts[2] if len(parts) == 3 else None
            
            # Construct event data
            event_data: EventPayload = {
                "project_id": proj_id,
                "event_type": event_type,
                "origin_module": origin_module,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pid": pid,
                "channel": channel
            }
            
            logger.debug(
                f"Received event: {event_type}",
                extra={
                    "project_id": proj_id,
                    "module": "event_bus",
                    "event_type": event_type,
                    "origin_module": origin_module
                }
            )
            
            # Execute callbacks using TaskGroup (Python 3.13)
            if event_type in self.callbacks:
                try:
                    async with asyncio.TaskGroup() as tg:
                        for callback in self.callbacks[event_type]:
                            tg.create_task(
                                self._execute_callback(callback, event_data)
                            )
                except* Exception as eg:  # Python 3.13 ExceptionGroup
                    for exc in eg.exceptions:
                        logger.error(
                            f"Callback execution failed: {type(exc).__name__}: {exc}",
                            exc_info=exc,
                            extra={
                                "project_id": proj_id,
                                "module": "event_bus",
                                "event_type": event_type
                            }
                        )
        
        except Exception as e:
            logger.error(
                f"Notification handler error: {type(e).__name__}: {e}",
                exc_info=True,
                extra={"project_id": self.project_id, "module": "event_bus"}
            )
    
    async def _execute_callback(
        self,
        callback: EventCallback,
        event_data: EventPayload
    ) -> None:
        """Execute single callback (sync or async)."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event_data)
            else:
                await asyncio.to_thread(callback, event_data)
                
        except Exception as e:
            logger.error(
                f"Callback {callback.__name__} failed: {type(e).__name__}: {e}",
                exc_info=True,
                extra={
                    "project_id": self.project_id,
                    "module": "event_bus",
                    "event_type": event_data.get("event_type")
                }
            )
    
    def register_callback(self, event_type: str, callback: EventCallback) -> None:
        """
        Register callback for specific event type.
        
        Thread-safe. Can be called before or after connect().
        
        Args:
            event_type: Event type to listen for
            callback: Function to call (sync or async)
        """
        self.callbacks[event_type].append(callback)
        
        logger.debug(
            f"Callback registered for event: {event_type}",
            extra={
                "project_id": self.project_id,
                "module": "event_bus",
                "callback": callback.__name__
            }
        )
    
    async def emit(
        self,
        project_id: str,
        event_type: str,
        origin_module: str | None = None
    ) -> None:
        """
        Emit event to PostgreSQL NOTIFY channel.
        
        Args:
            project_id: Source project identifier
            event_type: Type of event
            origin_module: Module that emitted the event
            
        Note:
            Rate limited to 1 emission per second per event_type.
            Payload format: "project_id:event_type:origin_module"
        """
        if self._connection is None or self._connection.is_closed():
            raise EventBusNotConnectedError(
                "EventBus not connected - call connect() first"
            )
        
        # Rate limiting check
        now = asyncio.get_event_loop().time()
        last_emit = self._last_emit_time.get(event_type, 0)
        
        if now - last_emit < self._emit_cooldown_seconds:
            logger.debug(
                f"Event {event_type} rate limited",
                extra={"project_id": project_id, "module": "event_bus"}
            )
            return
        
        try:
            # Format payload: "project_id:event_type:origin_module"
            module_part = f":{origin_module}" if origin_module else ""
            payload = f"{project_id}:{event_type}{module_part}"
            
            # Ensure payload is within PostgreSQL limit (8000 bytes)
            if len(payload) > 7900:
                logger.warning(
                    f"Payload too large ({len(payload)} bytes), truncating",
                    extra={"project_id": project_id, "module": "event_bus"}
                )
                payload = payload[:7900]
            
            # Execute NOTIFY
            await self._connection.execute(
                "SELECT pg_notify($1, $2)",
                "orchestrator_events",
                payload
            )
            
            self._last_emit_time[event_type] = now
            
            logger.debug(
                f"Event emitted: {event_type}",
                extra={
                    "project_id": project_id,
                    "module": "event_bus",
                    "event_type": event_type,
                    "origin_module": origin_module
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to emit event: {type(e).__name__}: {e}",
                exc_info=True,
                extra={
                    "project_id": project_id,
                    "module": "event_bus",
                    "event_type": event_type
                }
            )
    
    async def disconnect(self) -> None:
        """Gracefully disconnect from PostgreSQL (idempotent)."""
        self.running = False
        
        if self._connection is not None and not self._connection.is_closed():
            try:
                await self._connection.execute("UNLISTEN orchestrator_events")
                await self._connection.close()
                
                logger.info(
                    "EventBus disconnected gracefully",
                    extra={"project_id": self.project_id, "module": "event_bus"}
                )
            except Exception as e:
                logger.error(
                    f"Error during disconnect: {type(e).__name__}: {e}",
                    exc_info=True,
                    extra={"project_id": self.project_id, "module": "event_bus"}
                )
            finally:
                self._connection = None
    
    @classmethod
    async def get_instance(
        cls,
        project_id: str = "healer_nexus",
        database_url: str | None = None
    ) -> EventBus:
        """
        Get or create singleton EventBus instance (thread-safe).
        
        Args:
            project_id: Project identifier
            database_url: PostgreSQL URL (auto-detected if None)
            
        Returns:
            EventBus singleton instance
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(project_id, database_url)
            return cls._instance


# ============================================
# PUBLIC API - ModuleRegistry Compatible
# ============================================

async def get_event_bus(
    project_id: str = "healer_nexus",
    database_url: str | None = None
) -> EventBus:
    """
    Get EventBus singleton (ModuleRegistry compatible signature).
    
    Args:
        project_id: Project identifier (first positional arg for registry)
        database_url: PostgreSQL URL (optional, auto-detected from env)
        
    Returns:
        EventBus instance (NOT connected yet - call .connect())
    """
    return await EventBus.get_instance(project_id, database_url)