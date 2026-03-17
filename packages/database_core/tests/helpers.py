"""Test helpers for database_core package.

This module provides package-local test utilities that don't depend on
other packages' testing modules, keeping database_core architecturally
independent.
"""

from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.exceptions import DatabaseError


async def count_language_table_words(language: str, *, backend: AbstractBackend) -> int:
    """Count total word rows in the words_{language} table.

    This is a package-local test helper for verifying table lifecycle
    behavior in database_core integration tests. It counts all canonical
    word entries in the specified language table, independent of user
    associations.

    Args:
        language: Language code (e.g., "de", "fr") for the words table
        backend: Backend instance to execute the query

    Returns:
        Number of word rows in the words_{language} table

    Raises:
        DatabaseError: If the query fails
    """
    conn = await backend._connect()  # noqa: SLF001
    try:
        row = await conn.fetchrow(
            f"SELECT COUNT(*) AS cnt FROM words_{language}",  # noqa: S608
        )
        return int(row["cnt"])  # type: ignore[index]
    except Exception as exc:
        raise DatabaseError(str(exc)) from exc
