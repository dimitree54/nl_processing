"""Tiered exercise backend operations for Neon PostgreSQL.

Asyncpg wrappers for repeat-state table operations.
"""

import asyncpg

from nl_processing.database_core.backend._tiered_queries import (
    create_tiered_repeat_state_table,
    delete_repeat_state,
    get_repeat_state,
    get_repeat_states,
    upsert_repeat_state,
)
from nl_processing.database_core.exceptions import DatabaseError


async def create_tiered_tables(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    pairs: list[tuple[str, str]],
) -> None:
    """Create tiered repeat-state tables for all language pairs."""
    try:
        for src, tgt in pairs:
            await conn.execute(create_tiered_repeat_state_table(src, tgt))
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def upsert_repeat_state_impl(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    src: str,
    tgt: str,
    user_id: str,
    mode_slug: str,
    source_word_id: int,
) -> None:
    """Upsert repeat-state row (idempotent activation)."""
    try:
        await conn.execute(
            upsert_repeat_state(src, tgt),
            user_id,
            mode_slug,
            source_word_id,
        )
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def delete_repeat_state_impl(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    src: str,
    tgt: str,
    user_id: str,
    mode_slug: str,
    source_word_id: int,
) -> None:
    """Delete repeat-state row by (user_id, mode_slug, source_word_id)."""
    try:
        await conn.execute(
            delete_repeat_state(src, tgt),
            user_id,
            mode_slug,
            source_word_id,
        )
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def get_repeat_states_impl(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    src: str,
    tgt: str,
    user_id: str,
    mode_slug: str,
) -> list[dict[str, str | int]]:
    """Get all repeat-state rows for a user and mode_slug."""
    try:
        rows = await conn.fetch(get_repeat_states(src, tgt), user_id, mode_slug)
        return [dict(row) for row in rows]
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def get_repeat_state_impl(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    src: str,
    tgt: str,
    user_id: str,
    mode_slug: str,
    source_word_id: int,
) -> dict[str, str | int] | None:
    """Get one repeat-state row for (user_id, mode_slug, source_word_id)."""
    try:
        row = await conn.fetchrow(get_repeat_state(src, tgt), user_id, mode_slug, source_word_id)
        return dict(row) if row is not None else None
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
