"""Helper functions for user-related operations in NeonBackend."""

from datetime import datetime

import asyncpg

from nl_processing.database.backend._neon_helpers import infer_target_language
from nl_processing.database.backend._queries import ADD_USER_WORD, add_translation_link_query, get_user_words_query
from nl_processing.database.exceptions import DatabaseError


async def add_translation_link(conn: asyncpg.Connection, table: str, source_id: int, target_id: int) -> None:  # type: ignore[type-arg]
    """Add translation link between source and target word IDs."""
    try:
        await conn.execute(add_translation_link_query(table), source_id, target_id)
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def add_user_word(conn: asyncpg.Connection, user_id: str, word_id: int, language: str) -> None:  # type: ignore[type-arg]
    """Associate a word with a user."""
    try:
        await conn.execute(ADD_USER_WORD, user_id, word_id, language)
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc


async def get_user_words(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    user_id: str,
    language: str,
    word_type: str | None = None,
    limit: int | None = None,
    random: bool = False,
) -> list[dict[str, str | int | datetime]]:
    """Get user words with translations."""
    target_lang = infer_target_language(language)
    query = get_user_words_query(language, language, target_lang, word_type, limit, random)
    args: list[str | int] = [user_id, language]
    if word_type is not None:
        args.append(word_type)
    if limit is not None:
        args.append(limit)
    try:
        rows = await conn.fetch(query, *args)
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
    return [dict(row) for row in rows]
