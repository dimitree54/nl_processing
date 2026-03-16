"""Connection management for NeonBackend.

Extracted from neon.py to keep under 200-line limit.
"""

import asyncpg

from nl_processing.database_core.exceptions import DatabaseError
from nl_processing.database_core.logging import get_logger

_logger = get_logger("backend")


class ConnectionManager:
    """Manages database connections for NeonBackend."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._connection: asyncpg.Connection | None = None  # type: ignore[type-arg]

    async def get_connection(self) -> asyncpg.Connection:  # type: ignore[type-arg]
        """Get the shared connection, creating it if needed."""
        if self._connection is None:
            try:
                self._connection = await asyncpg.connect(dsn=self._database_url)
                _logger.info("Connected to Neon PostgreSQL")
            except asyncpg.PostgresError as exc:
                raise DatabaseError(str(exc)) from exc
            except OSError as exc:
                raise DatabaseError(str(exc)) from exc
        if self._connection is None:
            raise DatabaseError("Database connection was not initialized")
        return self._connection

    async def create_fresh_connection(self) -> asyncpg.Connection:  # type: ignore[type-arg]
        """Create a new connection for background tasks to avoid concurrency issues."""
        try:
            return await asyncpg.connect(dsn=self._database_url)
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc
        except OSError as exc:
            raise DatabaseError(str(exc)) from exc

    def get_database_url(self) -> str:
        """Get the database URL for creating new instances."""
        return self._database_url
