"""Delete operations extracted from NeonBackend.

Keeps the main neon.py module under the 200-line limit.
"""

import asyncpg

from nl_processing.database.backend._queries_delete import (
    check_user_word_exists_query,
    delete_user_exercise_score_query,
    delete_user_word_query,
)
from nl_processing.database.exceptions import DatabaseError


async def check_word_exists(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    user_id: str,
    source_word_id: int,
    language: str,
) -> bool:
    """Check if a source word is in the user's vocabulary."""
    try:
        query = check_user_word_exists_query(language)
        row = await conn.fetchrow(query, user_id, source_word_id, language)
        return row is not None
    except asyncpg.PostgresError as e:
        raise DatabaseError(f"Failed to check user word existence: {e}") from e


async def delete_word_membership(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    user_id: str,
    source_word_id: int,
    language: str,
) -> None:
    """Delete the user's membership row for a source word."""
    try:
        query = delete_user_word_query()
        await conn.execute(query, user_id, source_word_id, language)
    except asyncpg.PostgresError as e:
        raise DatabaseError(f"Failed to delete user word membership: {e}") from e


async def delete_exercise_score(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    table: str,
    user_id: str,
    source_word_id: int,
) -> None:
    """Delete the user's exercise score for a source word in one exercise table."""
    try:
        query = delete_user_exercise_score_query(table)
        await conn.execute(query, user_id, source_word_id)
    except asyncpg.PostgresError as e:
        raise DatabaseError(f"Failed to delete user exercise score: {e}") from e
