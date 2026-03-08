"""SQLite data-access layer for the local word-pair / score cache."""

from datetime import UTC, datetime
import json
import sqlite3

import aiosqlite

from nl_processing.database_cache._local_store_queries import (
    ALL_DDL,
    INSERT_PENDING_EVENT,
    INSERT_SCORE,
    INSERT_WORD_PAIR,
    UPSERT_SCORE,
)
from nl_processing.database_cache.exceptions import CacheStorageError


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


class LocalStore:
    """Async SQLite store for cached word pairs, scores, and pending events."""

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
        try:
            self._db = await aiosqlite.connect(self._db_path)
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode=WAL")
            for ddl in ALL_DDL:
                await self._db.execute(ddl)
            await self._db.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def close(self) -> None:
        """Close the SQLite connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def get_cached_word_pairs(
        self,
        word_type: str | None = None,
        limit: int | None = None,
        *,
        random: bool = False,
    ) -> list[dict[str, str | int]]:
        """Query cached word pairs with optional filter, limit, and random ordering."""
        sql = "SELECT * FROM cached_word_pairs"
        params: list[str | int] = []
        if word_type is not None:
            sql += " WHERE source_word_type = ?"
            params.append(word_type)
        if random:
            sql += " ORDER BY RANDOM()"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return await self._fetch_all(sql, params)

    async def get_cached_word_pairs_with_scores(self, exercise_types: list[str]) -> list[dict[str, str | int]]:
        """Query word pairs and attach scores per exercise type (missing = 0)."""
        try:
            rows = await self._fetch_all("SELECT * FROM cached_word_pairs")
            for row in rows:
                for et in exercise_types:
                    sc = await self._conn.execute(
                        "SELECT score FROM cached_scores WHERE source_word_id=? AND exercise_type=?",
                        (row["source_word_id"], et),
                    )
                    score_row = await sc.fetchone()
                    row[f"score_{et}"] = int(score_row["score"]) if score_row else 0
            return rows
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def get_pending_events(self) -> list[dict[str, str | int]]:
        return await self._fetch_all("SELECT * FROM pending_score_events WHERE flushed_at IS NULL ORDER BY created_at")

    async def get_pending_event_count(self) -> int:
        try:
            cur = await self._conn.execute("SELECT COUNT(*) FROM pending_score_events WHERE flushed_at IS NULL")
            row = await cur.fetchone()
            return int(row[0]) if row else 0
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def get_metadata(self) -> dict[str, str | int] | None:
        try:
            cur = await self._conn.execute("SELECT * FROM cache_metadata WHERE id = 1")
            row = await cur.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def has_snapshot(self) -> bool:
        try:
            cur = await self._conn.execute("SELECT 1 FROM cached_word_pairs LIMIT 1")
            return (await cur.fetchone()) is not None
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def record_score_and_event(
        self,
        source_word_id: int,
        exercise_type: str,
        delta: int,
        event_id: str,
    ) -> None:
        """Atomically upsert a cached score and insert a pending event."""
        now = _now()
        try:
            await self._conn.execute(UPSERT_SCORE, (source_word_id, exercise_type, delta, now, delta, now))
            await self._conn.execute(INSERT_PENDING_EVENT, (event_id, source_word_id, exercise_type, delta, now))
            await self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def rebuild_snapshot(
        self,
        word_pairs: list[tuple[int, str, str, int, str, str]],
        scores: dict[tuple[int, str], int],
    ) -> None:
        """Atomically replace cached word pairs and scores, then reapply pending events."""
        now = _now()
        try:
            await self._conn.execute("DELETE FROM cached_word_pairs")
            await self._conn.execute("DELETE FROM cached_scores")
            for wp in word_pairs:
                await self._conn.execute(INSERT_WORD_PAIR, wp)
            for (wid, et), score in scores.items():
                await self._conn.execute(INSERT_SCORE, (wid, et, score, now))
            for evt in await self.get_pending_events():
                await self._conn.execute(
                    UPSERT_SCORE,
                    (evt["source_word_id"], evt["exercise_type"], evt["delta"], now, evt["delta"], now),
                )
            await self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def mark_event_flushed(self, event_id: str) -> None:
        await self._exec_commit("UPDATE pending_score_events SET flushed_at=? WHERE event_id=?", (_now(), event_id))

    async def mark_event_failed(self, event_id: str, error: str) -> None:
        await self._exec_commit("UPDATE pending_score_events SET last_error=? WHERE event_id=?", (error, event_id))

    async def update_metadata(self, **fields: str | int | None) -> None:
        if not fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        await self._exec_commit(
            f"UPDATE cache_metadata SET {set_clause} WHERE id = 1",  # noqa: S608
            tuple(fields.values()),
        )

    async def ensure_metadata(self, exercise_types: list[str]) -> None:
        await self._exec_commit(
            "INSERT OR REPLACE INTO cache_metadata (id, exercise_types, schema_version) VALUES (1, ?, 1)",
            (json.dumps(exercise_types),),
        )

    async def get_source_word_id(self, normalized_form: str, word_type: str) -> int | None:
        """Look up a source_word_id from cached_word_pairs."""
        try:
            cur = await self._conn.execute(
                "SELECT source_word_id FROM cached_word_pairs WHERE source_normalized_form=? AND source_word_type=?",
                (normalized_form, word_type),
            )
            row = await cur.fetchone()
            return int(row["source_word_id"]) if row else None
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

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
