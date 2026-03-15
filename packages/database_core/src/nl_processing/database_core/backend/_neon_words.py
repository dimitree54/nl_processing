"""Word operations extracted from NeonBackend.

Keeps the main neon.py module under the 200-line limit.
"""

import asyncpg

from nl_processing.database_core.backend._queries import (
    add_word_query,
    count_user_words_query,
    get_word_query,
)
from nl_processing.database_core.exceptions import DatabaseError


async def add_word(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    normalized_form: str,
    word_type: str,
) -> int | None:
    """Insert word if not exists, return row id."""
    try:
        row = await conn.fetchrow(add_word_query(table), normalized_form, word_type)
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
    if row is None:
        return None
    return int(row["id"])


async def get_word(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    normalized_form: str,
) -> dict[str, str | int] | None:
    """Return row dict {id, normalized_form, word_type} or None."""
    try:
        row = await conn.fetchrow(get_word_query(table), normalized_form)
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
    if row is None:
        return None
    return {
        "id": row["id"],
        "normalized_form": row["normalized_form"],
        "word_type": row["word_type"],
    }


async def count_user_words(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    user_id: str,
    language: str,
    word_type: str | None = None,
) -> int:
    """Return total user-word associations for the given user and language."""
    args: list[str] = [user_id, language]
    if word_type is not None:
        args.append(word_type)
    try:
        count = await conn.fetchval(count_user_words_query(language, word_type), *args)
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
    if count is None:
        return 0
    return int(count)
