"""Test utilities for database module. NOT for production use."""

import os

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.exceptions import DatabaseError


def _get_backend(backend: NeonBackend | None) -> NeonBackend:
    if backend is not None:
        return backend
    return NeonBackend(os.environ["DATABASE_URL"])


async def drop_all_tables(
    languages: list[str],
    pairs: list[tuple[str, str]],
    exercise_slugs: list[str],
    *,
    backend: NeonBackend | None = None,
) -> None:
    """Drop all module-managed tables in FK-respecting order. IRREVERSIBLE.

    This is a **test-only** utility — never import from production code.

    Drop order (respects foreign key constraints):
    1. ``user_word_exercise_scores_{src}_{tgt}_{slug}`` for each pair/slug
    2. ``applied_events_{src}_{tgt}`` for each pair
    3. ``word_details_{src}_{tgt}`` for each pair
    4. ``translations_{src}_{tgt}`` for each pair
    5. ``user_words``
    6. ``words_{lang}`` for each language
    """
    b = _get_backend(backend)
    conn = await b._connect()  # noqa: SLF001
    try:
        for src, tgt in pairs:
            for slug in exercise_slugs:
                await conn.execute(
                    f"DROP TABLE IF EXISTS user_word_exercise_scores_{src}_{tgt}_{slug}",  # noqa: S608
                )
            await conn.execute(
                f"DROP TABLE IF EXISTS applied_events_{src}_{tgt}",  # noqa: S608
            )
        for src, tgt in pairs:
            await conn.execute(
                f"DROP TABLE IF EXISTS word_details_{src}_{tgt}",  # noqa: S608
            )
        for src, tgt in pairs:
            await conn.execute(
                f"DROP TABLE IF EXISTS translations_{src}_{tgt}",  # noqa: S608
            )
        await conn.execute("DROP TABLE IF EXISTS user_words")
        for lang in languages:
            await conn.execute(
                f"DROP TABLE IF EXISTS words_{lang}",  # noqa: S608
            )
    except Exception as exc:
        raise DatabaseError(str(exc)) from exc


async def reset_database(
    languages: list[str],
    pairs: list[tuple[str, str]],
    exercise_slugs: list[str],
    *,
    backend: NeonBackend | None = None,
) -> None:
    """Drop all tables and recreate them empty. IRREVERSIBLE.

    This is a **test-only** utility — never import from production code.
    Equivalent to ``drop_all_tables`` followed by ``create_tables``.
    """
    b = _get_backend(backend)
    await drop_all_tables(languages, pairs, exercise_slugs, backend=b)
    await b.create_tables(languages, pairs, exercise_slugs)


async def count_words(
    table: str,
    *,
    backend: NeonBackend | None = None,
) -> int:
    """Return the number of rows in ``words_{table}``. For test assertions.

    This is a **test-only** utility — never import from production code.
    """
    b = _get_backend(backend)
    conn = await b._connect()  # noqa: SLF001
    try:
        row = await conn.fetchrow(
            f"SELECT COUNT(*) AS cnt FROM words_{table}",  # noqa: S608
        )
    except Exception as exc:
        raise DatabaseError(str(exc)) from exc
    return int(row["cnt"])  # type: ignore[index]


async def count_user_words(
    user_id: str,
    language: str,
    *,
    backend: NeonBackend | None = None,
) -> int:
    """Return the number of words associated with a user. For test assertions.

    This is a **test-only** utility — never import from production code.
    """
    b = _get_backend(backend)
    conn = await b._connect()  # noqa: SLF001
    try:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS cnt FROM user_words WHERE user_id = $1 AND language = $2",
            user_id,
            language,
        )
    except Exception as exc:
        raise DatabaseError(str(exc)) from exc
    return int(row["cnt"])  # type: ignore[index]


async def count_translation_links(
    table: str,
    *,
    backend: NeonBackend | None = None,
) -> int:
    """Return the number of translation links in ``translations_{table}``. For test assertions.

    This is a **test-only** utility — never import from production code.
    """
    b = _get_backend(backend)
    conn = await b._connect()  # noqa: SLF001
    try:
        row = await conn.fetchrow(
            f"SELECT COUNT(*) AS cnt FROM translations_{table}",  # noqa: S608
        )
    except Exception as exc:
        raise DatabaseError(str(exc)) from exc
    return int(row["cnt"])  # type: ignore[index]
