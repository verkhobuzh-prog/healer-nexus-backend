"""
Backward compatibility: re-export database connection from app.database.connection.
Prefer: from app.database.connection import get_db, init_db, async_session_maker
"""
from app.database.connection import (
    engine,
    async_session_maker,
    get_db,
    init_db,
    check_db_health,
    emit_event,
    save_message,
    get_history,
)

__all__ = [
    "engine",
    "async_session_maker",
    "get_db",
    "init_db",
    "check_db_health",
    "emit_event",
    "save_message",
    "get_history",
]
