"""Package-local real-database helpers for database_cache E2E tests."""

from nl_processing.database_core.backend.neon import NeonBackend
from nl_processing.database_core.exceptions import DatabaseError


async def drop_all_tables(
    languages: list[str],
    pairs: list[tuple[str, str]],
    exercise_slugs: list[str],
    *,
    backend: NeonBackend,
) -> None:
    """Drop all remote tables used by the E2E cache fixtures."""
    conn = await backend._connect()  # noqa: SLF001
    try:
        for src, tgt in pairs:
            for slug in exercise_slugs:
                await conn.execute(f"DROP TABLE IF EXISTS user_word_exercise_scores_{src}_{tgt}_{slug}")  # noqa: S608
            await conn.execute(f"DROP TABLE IF EXISTS applied_events_{src}_{tgt}")  # noqa: S608
        for src, tgt in pairs:
            await conn.execute(f"DROP TABLE IF EXISTS word_details_{src}_{tgt}")  # noqa: S608
        for src, tgt in pairs:
            await conn.execute(f"DROP TABLE IF EXISTS translations_{src}_{tgt}")  # noqa: S608
        await conn.execute("DROP TABLE IF EXISTS user_words")
        for lang in languages:
            await conn.execute(f"DROP TABLE IF EXISTS words_{lang}")  # noqa: S608
    except Exception as exc:
        raise DatabaseError(str(exc)) from exc


async def reset_database(
    languages: list[str],
    pairs: list[tuple[str, str]],
    exercise_slugs: list[str],
    *,
    backend: NeonBackend,
) -> None:
    """Drop and recreate the remote schema used by cache E2E tests."""
    await drop_all_tables(languages, pairs, exercise_slugs, backend=backend)
    await backend.create_tables(languages, pairs, exercise_slugs)
