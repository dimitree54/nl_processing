"""Helper functions for detailed word operations in NeonBackend."""

import asyncpg

from nl_processing.database.backend._queries_detailed import (
    get_word_details_batch_query,
    get_word_details_query,
    upsert_word_details_query,
)
from nl_processing.database.exceptions import DatabaseError


async def upsert_details(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    source_word_id: int,
    word_type: str,
    schema_key: str,
    schema_version: int,
    payload: str,
) -> None:
    """Upsert detailed word record."""
    try:
        await conn.execute(
            upsert_word_details_query(table),
            source_word_id,
            word_type,
            schema_key,
            schema_version,
            payload,
        )
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def get_details(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    source_word_id: int,
    word_type: str,
) -> dict[str, str | int] | None:
    """Get detailed word record."""
    try:
        row = await conn.fetchrow(
            get_word_details_query(table),
            source_word_id,
            word_type,
        )
        return dict(row) if row else None
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def get_details_batch(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    source_word_ids_and_types: list[tuple[int, str]],
) -> list[dict[str, str | int]]:
    """Get detailed word records for multiple (source_word_id, word_type) pairs."""
    if not source_word_ids_and_types:
        return []

    try:
        count = len(source_word_ids_and_types)
        query = get_word_details_batch_query(table, count)

        # Flatten the list of tuples for the query parameters
        args = []
        for word_id, word_type in source_word_ids_and_types:
            args.extend([word_id, word_type])

        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
