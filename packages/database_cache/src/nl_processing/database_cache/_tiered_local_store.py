"""SQLite data-access layer for the tiered exercise cache."""

import json
import sqlite3

from nl_processing.database_cache._local_store_base import LocalStoreBase, _now
from nl_processing.database_cache._tiered_queries import (
    ALL_TIERED_DDL,
    DELETE_TIERED_REPEAT_STATE,
    INSERT_TIERED_PENDING_EVENT,
    INSERT_TIERED_REPEAT_STATE,
    INSERT_TIERED_WORD_PAIR,
    UPSERT_TIERED_SCORE,
)
from nl_processing.database_cache.exceptions import CacheStorageError


class TieredLocalStore(LocalStoreBase):
    """Async SQLite store for tiered exercise cache with repeat-state management."""

    async def open(self) -> None:
        """Open the SQLite connection and create tiered tables."""
        if self._db is not None:
            return
        try:
            self._db = await self._init_connection()
            for ddl in ALL_TIERED_DDL:
                await self._db.execute(ddl)
            await self._db.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def get_tiered_candidates(self, mode_slug: str, exercise_types: list[str]) -> list[dict[str, str | int]]:
        """Query tiered candidates joining snapshot + scores + repeat-state."""
        try:
            rows = await self._fetch_all("SELECT * FROM tiered_cached_word_pairs")
            for row in rows:
                # Attach scores for each exercise type (missing = 0)
                for et in exercise_types:
                    score_cursor = await self._conn.execute(
                        "SELECT score FROM tiered_cached_scores WHERE source_word_id=? AND exercise_type=?",
                        (row["source_word_id"], et),
                    )
                    score_row = await score_cursor.fetchone()
                    row[f"score_{et}"] = int(score_row["score"]) if score_row else 0

                # Check repeat-state
                repeat_cursor = await self._conn.execute(
                    "SELECT 1 FROM tiered_repeat_state WHERE mode_slug=? AND source_word_id=?",
                    (mode_slug, row["source_word_id"]),
                )
                row["in_repeat_mode"] = (await repeat_cursor.fetchone()) is not None

            return rows
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def get_tiered_pending_events(self) -> list[dict[str, str | int]]:
        """Get unflushed tiered pending events."""
        return await self._fetch_all("SELECT * FROM tiered_pending_events WHERE flushed_at IS NULL ORDER BY created_at")

    async def get_tiered_pending_event_count(self) -> int:
        """Count unflushed tiered pending events."""
        try:
            cursor = await self._conn.execute("SELECT COUNT(*) FROM tiered_pending_events WHERE flushed_at IS NULL")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def record_tiered_score_and_event(
        self,
        mode_slug: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
        event_id: str,
        next_in_repeat: bool,
    ) -> None:
        """Atomically upsert score, update repeat-state, and insert pending event."""
        now = _now()
        try:
            # Update score
            await self._conn.execute(UPSERT_TIERED_SCORE, (source_word_id, exercise_type, delta, now, delta, now))

            # Update repeat-state
            if next_in_repeat:
                await self._conn.execute(INSERT_TIERED_REPEAT_STATE, (mode_slug, source_word_id, now))
            else:
                await self._conn.execute(DELETE_TIERED_REPEAT_STATE, (mode_slug, source_word_id))

            # Insert pending event
            await self._conn.execute(
                INSERT_TIERED_PENDING_EVENT, (event_id, mode_slug, source_word_id, exercise_type, delta, now)
            )

            await self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def rebuild_tiered_snapshot(
        self,
        word_pairs: list[tuple[int, str, str, int, str, str]],
        scores: dict[tuple[int, str], int],
        repeat_states: dict[tuple[str, int], str],
    ) -> None:
        """Atomically replace snapshot + scores + repeat-state, then reapply pending events."""
        now = _now()
        try:
            # Clear existing data
            await self._conn.execute("DELETE FROM tiered_cached_word_pairs")
            await self._conn.execute("DELETE FROM tiered_cached_scores")
            await self._conn.execute("DELETE FROM tiered_repeat_state")

            # Insert word pairs
            for wp in word_pairs:
                await self._conn.execute(INSERT_TIERED_WORD_PAIR, wp)

            # Insert scores
            for (source_word_id, exercise_type), score in scores.items():
                await self._conn.execute(
                    "INSERT INTO tiered_cached_scores (source_word_id, exercise_type, score, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (source_word_id, exercise_type, score, now),
                )

            # Insert repeat states
            for (mode_slug, source_word_id), activated_at in repeat_states.items():
                await self._conn.execute(INSERT_TIERED_REPEAT_STATE, (mode_slug, source_word_id, activated_at))

            # Reapply pending events
            pending_events = await self.get_tiered_pending_events()
            for event in pending_events:
                await self._conn.execute(
                    UPSERT_TIERED_SCORE,
                    (event["source_word_id"], event["exercise_type"], event["delta"], now, event["delta"], now),
                )

            await self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def mark_tiered_event_flushed(self, event_id: str) -> None:
        """Mark a tiered event as flushed."""
        await self._exec_commit("UPDATE tiered_pending_events SET flushed_at=? WHERE event_id=?", (_now(), event_id))

    async def mark_tiered_event_failed(self, event_id: str, error: str) -> None:
        """Mark a tiered event as failed with error."""
        await self._exec_commit("UPDATE tiered_pending_events SET last_error=? WHERE event_id=?", (error, event_id))

    async def ensure_tiered_metadata(self, mode_slug: str, exercise_types: list[str]) -> None:
        """Ensure tiered metadata row exists with current parameters."""
        await self._exec_commit(
            "INSERT OR REPLACE INTO tiered_cache_metadata "
            "(id, mode_slug, exercise_types, schema_version) VALUES (1, ?, ?, 1)",
            (mode_slug, json.dumps(exercise_types)),
        )

    async def get_tiered_metadata(self) -> dict[str, str | int] | None:
        """Get tiered cache metadata."""
        try:
            cursor = await self._conn.execute("SELECT * FROM tiered_cache_metadata WHERE id = 1")
            row = await cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def has_tiered_snapshot(self) -> bool:
        """Check if tiered snapshot exists."""
        try:
            cursor = await self._conn.execute("SELECT 1 FROM tiered_cached_word_pairs LIMIT 1")
            return (await cursor.fetchone()) is not None
        except sqlite3.Error as exc:
            raise CacheStorageError(str(exc)) from exc

    async def update_tiered_metadata(self, **fields: str | int | None) -> None:
        """Update tiered metadata fields."""
        if not fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        await self._exec_commit(
            f"UPDATE tiered_cache_metadata SET {set_clause} WHERE id = 1",  # noqa: S608
            tuple(fields.values()),
        )
