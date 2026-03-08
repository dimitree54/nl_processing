"""Exercise-related backend operations extracted from NeonBackend.

Keeps the main neon.py module under the 200-line limit.
"""

import asyncpg

from nl_processing.database.backend._queries import (
    check_event_applied_query,
    create_applied_events_table,
    create_exercise_scores_table,
    get_scores_query,
    increment_score_query,
    mark_event_applied_query,
)
from nl_processing.database.exceptions import DatabaseError


async def create_exercise_tables(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    pairs: list[tuple[str, str]],
    exercise_slugs: list[str],
) -> None:
    """Create per-exercise-type score tables and applied_events tables."""
    try:
        for src, tgt in pairs:
            for slug in exercise_slugs:
                await conn.execute(create_exercise_scores_table(src, tgt, slug))
            await conn.execute(create_applied_events_table(src, tgt))
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def increment_score(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    user_id: str,
    source_word_id: int,
    delta: int,
) -> int:
    """Upsert exercise score by delta, return new score value."""
    try:
        row = await conn.fetchrow(
            increment_score_query(table),
            user_id,
            source_word_id,
            delta,
        )
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
    return int(row["score"])  # type: ignore[index]


async def get_scores(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    user_id: str,
    source_word_ids: list[int],
) -> list[dict[str, str | int]]:
    """Return exercise score rows for the given user and words."""
    if not source_word_ids:
        return []
    try:
        rows = await conn.fetch(get_scores_query(table), user_id, source_word_ids)
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
    return [dict(row) for row in rows]


async def check_event(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    event_id: str,
) -> bool:
    """Check if event_id exists in the applied_events table."""
    try:
        row = await conn.fetchrow(check_event_applied_query(table), event_id)
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
    return row is not None


async def mark_event(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    event_id: str,
) -> None:
    """Insert event_id into the applied_events table."""
    try:
        await conn.execute(mark_event_applied_query(table), event_id)
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def atomic_apply_delta(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    score_table: str,
    events_table: str,
    user_id: str,
    event_id: str,
    source_word_id: int,
    delta: int,
) -> bool:
    """Atomically check-apply-mark a score delta in one transaction."""
    try:
        async with conn.transaction():
            already = await conn.fetchrow(check_event_applied_query(events_table), event_id)
            if already is not None:
                return False
            await conn.fetchrow(
                increment_score_query(score_table),
                user_id,
                source_word_id,
                delta,
            )
            await conn.execute(mark_event_applied_query(events_table), event_id)
            return True
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
