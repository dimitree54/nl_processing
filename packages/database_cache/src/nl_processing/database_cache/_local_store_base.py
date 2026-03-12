"""Base infrastructure for SQLite storage operations."""

from datetime import UTC, datetime
import sqlite3

import aiosqlite

from nl_processing.database_cache._local_store_queries import ALL_DDL
from nl_processing.database_cache.exceptions import CacheStorageError


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


class LocalStoreBase:
    """Base class providing generic SQLite infrastructure methods."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    @property
    def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            raise CacheStorageError("LocalStore is not open")
        return self._db

    async def open(self) -> None:
        """Open the SQLite connection and create tables."""
        if self._db is not None:
            return
        try:
            self._db = await aiosqlite.connect(self._db_path)
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode=WAL")
            for ddl in ALL_DDL:
                await self._db.execute(ddl)
            # Schema migration: add added_at column if it doesn't exist
            try:
                await self._db.execute("ALTER TABLE cached_word_pairs ADD COLUMN added_at TEXT")
            except sqlite3.OperationalError:
                # Column already exists or other error, safe to ignore
                pass
            await self._db.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def close(self) -> None:
        """Close the SQLite connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def _fetch_all(self, sql: str, params: list[str | int] | None = None) -> list[dict[str, str | int]]:
        try:
            cur = await self._conn.execute(sql, params or [])
            return [dict(row) for row in await cur.fetchall()]
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def _exec_commit(self, sql: str, params: tuple[str | int | None, ...]) -> None:
        try:
            await self._conn.execute(sql, params)
            await self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc
