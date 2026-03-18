"""Shared fixtures for database e2e tests against real Neon PostgreSQL + OpenAI."""

from collections.abc import AsyncIterator
import os

from nl_processing.core.models import Language
from nl_processing.database_core.backend.neon import NeonBackend
from nl_processing.translate_word.service import WordTranslator
import pytest_asyncio

from nl_processing.database.service import DatabaseService
from tests.e2e.database.db_helpers import drop_all_tables, reset_database

_LANGUAGES = ["nl", "ru"]
_PAIRS = [("nl", "ru")]
_EXERCISE_SLUGS = ["flashcard"]


def make_service(user_id: str, *, backend: NeonBackend | None = None) -> DatabaseService:
    """Create a DatabaseService composed with the translate_word package."""
    return DatabaseService(
        user_id=user_id,
        backend=backend,
        translator=WordTranslator(source_language=Language.NL, target_language=Language.RU),
    )


async def cleanup_service(service: DatabaseService) -> None:
    """Drain background translations from a service before test teardown.

    Call this helper before teardown when your test uses a service
    that may have created background translation tasks.
    """
    await service.wait_for_background_translations()


@pytest_asyncio.fixture
async def db_ready() -> AsyncIterator[NeonBackend]:
    """Function-scoped fixture: reset DB before test, drop tables after.

    Acquires an exclusive advisory lock (key 12345) to serialize with
    integration tests that use shared locks on the same key.
    Yields the shared backend so tests and helpers reuse the same connection.
    """
    backend = NeonBackend(os.environ["DATABASE_URL"])
    conn = await backend._connect()  # noqa: SLF001
    await conn.execute("SELECT pg_advisory_lock(12345)")
    try:
        await reset_database(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS, backend=backend)
        yield backend
        await drop_all_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS, backend=backend)
        await backend.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
    finally:
        await conn.execute("SELECT pg_advisory_unlock(12345)")
