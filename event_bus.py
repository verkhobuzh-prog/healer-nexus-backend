"""
Event Bus using PostgreSQL LISTEN/NOTIFY for multi-project orchestration.

Architecture:
- Lazy loading of asyncpg to prevent import-time errors
- Singleton pattern with automatic config detection
- TYPE_CHECKING for IDE support without runtime overhead
- Python 3.13.11 compliant (TaskGroup, ExceptionGroup, PEP 695)

Author: Senior Backend Architect
Date: 2025-01-22
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

# Type-checking only imports (never loaded at runtime)
if TYPE_CHECKING:
    from asyncpg import Connection, PostgresError
else:
    # Runtime: Don't import anything yet (lazy loading)
    Connection = None
    PostgresError = Exception  # Fallback type for except blocks

# Python 3.13 type aliases (PEP 695)
type EventCallback = Callable[[dict[str, Any]], Any]  # Supports both sync and async
type EventPayload = dict[str, Any]

logger = logging.getLogger(__name__)


class EventBusError(Exception):
    """Base exception for EventBus errors."""
    pass


class EventBusConnectionError(EventBusError):
    """Raised when EventBus cannot connect to PostgreSQL."""
    pass


class EventBus:
    """
    PostgreSQL LISTEN/NOTIFY event bus for real-time multi-project orchestration.
    
    Features:
    - Lazy asyncpg loading (no import-time errors)
    - Automatic reconnection with exponential backoff
    - Graceful degradation when PostgreSQL unavailable
    - Thread-safe callback registration
    - Python 3.13 ExceptionGroup handling
    
    Example:
        >>> bus = EventBus.get_instance()
        >>> await bus.connect()
        >>> bus.register_callback("error", lambda evt: print(evt))
        >>> await bus.emit("healer_nexus", "test_event")
    """
    
    # Class-level singleton instance
    _instance: EventBus | None = None
    _lock = asyncio.Lock()
    
    def __init__(
        self,
        database_url: str | None = None,
        project_id: str = "healer_nexus"
    ):
        """
        Initialize EventBus.
        
        Args:
            database_url: PostgreSQL connection string. If None, reads from env.
            project_id: Project identifier for event emission
            
        Note:
            Do not instantiate directly. Use EventBus.get_instance() instead.
        """
        # Auto-detect database URL from environment if not provided
        if database_url is None:
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://localhost/healer_nexus"
            )
        
        self.database_url = database_url
        self.project_id = project_id
        self.running = False
        
        # Callbacks storage: {event_type: [callback1, callback2, ...]}
        self.callbacks: dict[str, list[EventCallback]] = defaultdict(list)
        
        # Connection state (string type hint for forward reference)
        self._connection: "Connection | None" = None
        self._asyncpg_module: Any = None  # Lazy-loaded module
        
        # Reconnection tracking
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_backoff_base = 2  # Exponential backoff multiplier
        
        # Rate limiting for event emission
        self._last_emit_time: dict[str, float] = {}
        self._emit_cooldown = 1.0  # seconds between same event types
        
        logger.info(
            "EventBus initialized",
            extra={"project_id": project_id, "database": database_url.split("@")[-1]}
        )
    
    def _lazy_load_asyncpg(self) -> Any:
        """
        Lazy load asyncpg module to prevent import-time errors.
        
        Returns:
            asyncpg module object
            
        Raises:
            ImportError: If asyncpg is not installed
        """
        if self._asyncpg_module is not None:
            return self._asyncpg_module
        
        try:
            import asyncpg as pg_module
            self._asyncpg_module = pg_module
            logger.debug("asyncpg module loaded successfully")
            return pg_module
        except ImportError as e:
            error_msg = (
                "asyncpg is required for EventBus. "
                "Install with: pip install asyncpg>=0.31.0"
            )
            logger.error(error_msg)
            raise ImportError(error_msg) from e
    
    async def connect(self) -> None:
        """
        Establish PostgreSQL connection and execute LISTEN.
        
        This method is idempotent - safe to call multiple times.
        
        Raises:
            ImportError: If asyncpg is not installed
            EventBusConnectionError: If connection fails after retries
        """
        if self._connection is not None and not self._connection.is_closed():
            logger.debug("EventBus already connected")
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
                timeout=15.0  # Total timeout including retries
            )
            
            # Execute LISTEN on orchestrator events channel
            await self._connection.execute("LISTEN orchestrator_events")
            
            self.running = True
            self._reconnect_attempts = 0
            
            logger.info(
                "EventBus connected to PostgreSQL",
                extra={
                    "project_id": self.project_id,
                    "channel": "orchestrator_events",
                    "server_version": self._connection.get_server_version()
                }
            )
            
        except asyncio.TimeoutError as e:
            error_msg = f"Connection timeout after 15s: {self.database_url}"
            logger.error(error_msg, exc_info=True)
            raise EventBusConnectionError(error_msg) from e
            
        except Exception as e:
            # Catch all asyncpg errors (they're loaded at runtime)
            error_msg = f"Failed to connect to PostgreSQL: {e}"
            logger.error(
                error_msg,
                exc_info=True,
                extra={"database_url": self.database_url.split("@")[-1]}
            )
            raise EventBusConnectionError(error_msg) from e
    
    async def listen(self) -> None:
        """
        Start listening for PostgreSQL notifications.
        
        This is a long-running coroutine that should be run in a background task.
        Automatically reconnects on connection loss with exponential backoff.
        
        Example:
            >>> asyncio.create_task(event_bus.listen())
        """
        # Ensure connected before listening
        if not self.running or self._connection is None:
            await self.connect()
        
        logger.info(
            "EventBus listener started",
            extra={"project_id": self.project_id}
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
                    # Check connection health every 30 seconds
                    await asyncio.sleep(30)
                    
                    if self._connection.is_closed():
                        logger.warning("Connection closed, triggering reconnect")
                        raise ConnectionError("PostgreSQL connection lost")
                    
                    # Send heartbeat query
                    try:
                        await asyncio.wait_for(
                            self._connection.fetchval("SELECT 1"),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Heartbeat timeout, connection may be stale")
                        raise ConnectionError("Heartbeat failed")
                
            except asyncio.CancelledError:
                logger.info("EventBus listener cancelled gracefully")
                break
            
            except Exception as e:
                logger.error(
                    f"EventBus listener error: {type(e).__name__}: {e}",
                    exc_info=True,
                    extra={"project_id": self.project_id}
                )
                
                # Attempt reconnection with exponential backoff
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    self._reconnect_attempts += 1
                    wait_time = min(
                        5 * (self._reconnect_backoff_base ** self._reconnect_attempts),
                        300  # Max 5 minutes
                    )
                    
                    logger.warning(
                        f"Reconnecting in {wait_time}s "
                        f"(attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})",
                        extra={"project_id": self.project_id}
                    )
                    
                    await asyncio.sleep(wait_time)
                    
                    try:
                        await self.connect()
                    except EventBusConnectionError:
                        logger.error("Reconnection failed, will retry")
                        continue
                else:
                    logger.critical(
                        "Max reconnection attempts reached - EventBus entering degraded mode",
                        extra={"project_id": self.project_id}
                    )
                    self.running = False
                    break
        
        logger.info("EventBus listener stopped")
    
    async def _on_notification(
        self,
        connection: Any,
        pid: int,
        channel: str,
        payload: str
    ) -> None:
        """
        Handle incoming PostgreSQL notification.
        
        Payload format: "project_id:event_type:module_name"
        
        Args:
            connection: PostgreSQL connection (asyncpg specific)
            pid: PostgreSQL backend PID
            channel: Notification channel name
            payload: Notification payload string
        """
        try:
            # Parse payload into components
            parts = payload.split(":", 2)
            
            if len(parts) < 2:
                logger.warning(
                    f"Invalid payload format (expected 'project:event:module'): {payload}",
                    extra={"channel": channel}
                )
                return
            
            proj_id = parts[0]
            event_type = parts[1]
            module_name = parts[2] if len(parts) == 3 else None
            
            # Construct event data
            event_data: EventPayload = {
                "project_id": proj_id,
                "event_type": event_type,
                "module_name": module_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pid": pid,
                "channel": channel
            }
            
            logger.debug(
                f"Received event: {event_type}",
                extra={
                    "project_id": proj_id,
                    "module_name": module_name,
                    "event_type": event_type
                }
            )
            
            # Execute registered callbacks for this event type
            if event_type in self.callbacks:
                # Use TaskGroup for parallel callback execution (Python 3.13)
                async with asyncio.TaskGroup() as tg:
                    for callback in self.callbacks[event_type]:
                        tg.create_task(self._execute_callback(callback, event_data))
            
        except* Exception as eg:  # Python 3.13 ExceptionGroup syntax
            # Handle multiple callback failures
            for exc in eg.exceptions:
                logger.error(
                    f"Notification handler error: {type(exc).__name__}: {exc}",
                    exc_info=exc
                )
        except Exception as e:
            # Fallback for single exceptions
            logger.error(
                f"Notification handler error: {type(e).__name__}: {e}",
                exc_info=True
            )
    
    async def _execute_callback(
        self,
        callback: EventCallback,
        event_data: EventPayload
    ) -> None:
        """
        Execute a single callback, handling both sync and async functions.
        
        Args:
            callback: Callback function (sync or async)
            event_data: Event payload to pass to callback
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event_data)
            else:
                # Run sync callback in executor to avoid blocking
                await asyncio.to_thread(callback, event_data)
                
        except Exception as e:
            logger.error(
                f"Callback execution failed: {callback.__name__}: {e}",
                exc_info=True,
                extra={"event_type": event_data.get("event_type")}
            )
    
    def register_callback(
        self,
        event_type: str,
        callback: EventCallback
    ) -> None:
        """
        Register callback for specific event type.
        
        Thread-safe. Can be called before or after connect().
        
        Args:
            event_type: Event type to listen for (e.g., "error", "health_degraded")
            callback: Function to call when event occurs (sync or async)
            
        Example:
            >>> def on_error(event):
            ...     print(f"Error: {event['module_name']}")
            >>> bus.register_callback("error", on_error)
        """
        self.callbacks[event_type].append(callback)
        logger.debug(
            f"Callback registered for event type: {event_type}",
            extra={"callback": callback.__name__}
        )
    
    async def emit(
        self,
        project_id: str,
        event_type: str,
        module_name: str | None = None,
        data: dict[str, Any] | None = None,
        severity: str = "info"
    ) -> None:
        """
        Emit event to PostgreSQL NOTIFY channel.
        
        Includes rate limiting to prevent notification spam.
        
        Args:
            project_id: Source project identifier
            event_type: Type of event (error, health_degraded, circuit_opened, etc)
            module_name: Optional module name
            data: Optional event data (for DB storage, not sent via NOTIFY)
            severity: Event severity (info, warning, critical)
            
        Note:
            Rate limited to 1 emission per second per event_type.
            Data dict is NOT sent via NOTIFY (PostgreSQL payload limit is 8000 bytes).
            Store large data in orchestrator_events table separately.
        """
        # Check connection
        if self._connection is None or self._connection.is_closed():
            logger.warning(
                "EventBus not connected - cannot emit event",
                extra={"event_type": event_type, "project_id": project_id}
            )
            return
        
        # Rate limiting check
        now = asyncio.get_event_loop().time()
        last_emit = self._last_emit_time.get(event_type, 0)
        
        if now - last_emit < self._emit_cooldown:
            logger.debug(
                f"Event {event_type} rate limited (cooldown: {self._emit_cooldown}s)",
                extra={"project_id": project_id}
            )
            return
        
        try:
            # Format payload for NOTIFY (max 8000 bytes)
            module_part = f":{module_name}" if module_name else ""
            payload = f"{project_id}:{event_type}{module_part}"
            
            # Ensure payload is within PostgreSQL limit
            if len(payload) > 7900:  # Leave buffer for encoding
                logger.warning(
                    f"Payload too large ({len(payload)} bytes), truncating",
                    extra={"event_type": event_type}
                )
                payload = payload[:7900]
            
            # Execute NOTIFY
            await self._connection.execute(
                "SELECT pg_notify($1, $2)",
                "orchestrator_events",
                payload
            )
            
            # Update rate limit tracker
            self._last_emit_time[event_type] = now
            
            logger.debug(
                f"Event emitted: {event_type}",
                extra={
                    "project_id": project_id,
                    "module_name": module_name,
                    "severity": severity
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to emit event: {type(e).__name__}: {e}",
                exc_info=True,
                extra={"event_type": event_type, "project_id": project_id}
            )
    
    async def disconnect(self) -> None:
        """
        Gracefully disconnect from PostgreSQL.
        
        Safe to call multiple times (idempotent).
        """
        self.running = False
        
        if self._connection is not None and not self._connection.is_closed():
            try:
                # Remove listener before closing
                await self._connection.execute("UNLISTEN orchestrator_events")
                
                # Close connection
                await self._connection.close()
                
                logger.info(
                    "EventBus disconnected gracefully",
                    extra={"project_id": self.project_id}
                )
            except Exception as e:
                logger.error(
                    f"Error during disconnect: {e}",
                    exc_info=True
                )
            finally:
                self._connection = None
    
    @classmethod
    async def get_instance(
        cls,
        database_url: str | None = None,
        project_id: str = "healer_nexus"
    ) -> EventBus:
        """
        Get or create singleton EventBus instance.
        
        Thread-safe with async lock.
        
        Args:
            database_url: PostgreSQL connection string (optional, reads from env)
            project_id: Project identifier (default: healer_nexus)
            
        Returns:
            EventBus singleton instance
            
        Example:
            >>> bus = await EventBus.get_instance()
            >>> await bus.connect()
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(database_url, project_id)
            return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset singleton instance (for testing only).
        
        Warning: Only use in test teardown. Not thread-safe.
        """
        cls._instance = None


# ============================================
# PUBLIC API - Compatible with ModuleRegistry
# ============================================

async def get_event_bus(
    project_id: str = "healer_nexus",
    database_url: str | None = None
) -> EventBus:
    """
    Get EventBus singleton instance (ModuleRegistry compatible signature).
    
    This function signature matches what ModuleRegistry expects:
    - project_id is first parameter (positional)
    - database_url is optional (auto-detected from env)
    
    Args:
        project_id: Project identifier
        database_url: Optional PostgreSQL URL (reads from DATABASE_URL env var if None)
        
    Returns:
        EventBus singleton instance (NOT connected yet - call .connect())
        
    Example:
        >>> # Called from ModuleRegistry
        >>> bus = await get_event_bus("healer_nexus")
        >>> await bus.connect()
        >>> bus.register_callback("error", handle_error)
    """
    return await EventBus.get_instance(database_url, project_id)


# ============================================
# INITIALIZATION HELPER
# ============================================

async def init_event_bus(
    database_url: str | None = None,
    project_id: str = "healer_nexus",
    auto_connect: bool = True
) -> EventBus:
    """
    Initialize and optionally connect EventBus.
    
    Call this from FastAPI lifespan startup.
    
    Args:
        database_url: PostgreSQL connection string (optional)
        project_id: Project identifier
        auto_connect: Whether to immediately connect (default: True)
        
    Returns:
        Connected EventBus instance
        
    Example:
        >>> # In app/main.py lifespan:
        >>> bus = await init_event_bus(auto_connect=True)
        >>> asyncio.create_task(bus.listen())
    """
    bus = await get_event_bus(project_id, database_url)
    
    if auto_connect:
        try:
            await bus.connect()
            logger.info("EventBus initialized and connected")
        except EventBusConnectionError as e:
            logger.error(f"EventBus connection failed: {e}")
            # Don't crash app - EventBus can be used in degraded mode
    
    return bus