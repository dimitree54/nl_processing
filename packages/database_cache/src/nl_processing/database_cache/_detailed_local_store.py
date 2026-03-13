"""Local SQLite storage for detailed word cache data."""

import sqlite3

from nl_processing.database_cache._detailed_queries import (
    CREATE_DETAILED_WORDS_TABLE,
    DELETE_DETAILED,
    INSERT_OR_REPLACE_DETAILED,
    SELECT_DETAILED,
)
from nl_processing.database_cache._local_store_base import LocalStoreBase, _now
from nl_processing.database_cache.exceptions import CacheStorageError


class DetailedLocalStore(LocalStoreBase):
    """Local SQLite storage for detailed word cache data."""

    async def open(self) -> None:
        """Open the SQLite connection and create detailed words table."""
        if self._db is not None:
            return
        try:
            self._db = await self._init_connection()
            await self._db.execute(CREATE_DETAILED_WORDS_TABLE)
            await self._db.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

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
