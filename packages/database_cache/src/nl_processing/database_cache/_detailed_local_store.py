"""Local SQLite storage for detailed word cache data."""

from datetime import UTC, datetime
import sqlite3

import aiosqlite

from nl_processing.database_cache._detailed_queries import (
    CREATE_DETAILED_WORDS_TABLE,
    DELETE_DETAILED,
    INSERT_OR_REPLACE_DETAILED,
    SELECT_DETAILED,
)
from nl_processing.database_cache.exceptions import CacheStorageError


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


class DetailedLocalStore:
    """Local SQLite storage for detailed word cache data."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    @property
    def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            raise CacheStorageError("DetailedLocalStore is not open")
        return self._db

    async def open(self) -> None:
        """Open the SQLite connection and create tables."""
        if self._db is not None:
            return
        try:
            self._db = await aiosqlite.connect(self._db_path)
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute(CREATE_DETAILED_WORDS_TABLE)
            await self._db.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def close(self) -> None:
        """Close the SQLite connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def get_cached_detail(self, source_word: str, word_type: str) -> dict[str, str | int] | None:
        """Fetch a single cached detailed word record."""
        try:
            cur = await self._conn.execute(SELECT_DETAILED, (source_word, word_type))
            row = await cur.fetchone()
            if row is None:
                return None
            return dict(row)
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def upsert_cached_detail(
        self,
        source_word: str,
        word_type: str,
        schema_key: str,
        schema_version: int,
        payload_json: str,
    ) -> None:
        """Insert or replace a cached detailed word record."""
        try:
            await self._conn.execute(
                INSERT_OR_REPLACE_DETAILED,
                (source_word, word_type, schema_key, schema_version, payload_json, _now()),
            )
            await self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def delete_cached_detail(self, source_word: str, word_type: str) -> None:
        """Delete a single cached detailed word record."""
        try:
            await self._conn.execute(DELETE_DETAILED, (source_word, word_type))
            await self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc
