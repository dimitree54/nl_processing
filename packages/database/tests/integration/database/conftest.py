"""Shared fixtures for database integration tests against real Neon PostgreSQL."""

from collections.abc import AsyncIterator, Awaitable, Callable
import os

from nl_processing.core.models import Language, PartOfSpeech
from nl_processing.database_core.backend.neon import NeonBackend
import pytest_asyncio

from tests.integration.database.seed_helpers import (
    SeededWordPair,
    make_unique_user_id,
    make_unique_word_form,
    seed_detail_row,
    seed_scores,
    seed_word_pair,
    seed_word_set,
)

_LANGUAGES = ["nl", "ru"]
_PAIRS = [("nl", "ru")]
_EXERCISE_SLUGS = ["flashcard"]


async def _close_backend_connection(backend: NeonBackend) -> None:
    """Close an open backend connection."""
    conn = backend._connection_manager._connection  # noqa: SLF001
    if conn is not None and not conn.is_closed():
        await conn.close()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def integration_schema_ready() -> None:
    """Create the shared integration schema once per module."""
    backend = NeonBackend(os.environ["DATABASE_URL"])
    try:
        await backend.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
    finally:
        await _close_backend_connection(backend)


@pytest_asyncio.fixture
async def neon_backend(integration_schema_ready: None) -> AsyncIterator[NeonBackend]:  # noqa: ARG001
    """Function-scoped fixture: give each test its own backend connection."""
    backend = NeonBackend(os.environ["DATABASE_URL"])
    try:
        yield backend
    finally:
        await _close_backend_connection(backend)


@pytest_asyncio.fixture
def make_seeded_word_pair(
    neon_backend: NeonBackend,
) -> Callable[..., Awaitable[SeededWordPair]]:
    """Factory fixture for seeding individual word pairs."""

    async def _seed_pair(
        source_form: str | None = None,
        target_form: str | None = None,
        user_id: str | None = None,
        word_type: PartOfSpeech = PartOfSpeech.NOUN,
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
    ) -> SeededWordPair:
        user_id = user_id or make_unique_user_id()
        source_form = source_form or make_unique_word_form("word")
        if target_form is True:  # type: ignore[comparison-overlap]
            target_form = f"ru_{source_form}"
        return await seed_word_pair(
            backend=neon_backend,
            user_id=user_id,
            source_form=source_form,
            target_form=target_form,
            word_type=word_type,
            source_language=source_language,
            target_language=target_language,
        )

    return _seed_pair


@pytest_asyncio.fixture
def make_seeded_word_set(
    neon_backend: NeonBackend,
) -> Callable[..., Awaitable[list[SeededWordPair]]]:
    """Factory fixture for seeding sets of word pairs."""

    async def _seed_set(
        word_specs: list[tuple[str, str | None, PartOfSpeech]],
        user_id: str | None = None,
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
    ) -> list[SeededWordPair]:
        user_id = user_id or make_unique_user_id()
        return await seed_word_set(
            backend=neon_backend,
            user_id=user_id,
            word_specs=word_specs,
            source_language=source_language,
            target_language=target_language,
        )

    return _seed_set


@pytest_asyncio.fixture
def seed_word_scores(neon_backend: NeonBackend) -> Callable[..., Awaitable[None]]:
    """Factory fixture for attaching scores to seeded words."""

    async def _seed_scores(
        source_word_id: int,
        user_id: str,
        scores: dict[str, int],
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
    ) -> None:
        return await seed_scores(
            backend=neon_backend,
            source_word_id=source_word_id,
            user_id=user_id,
            scores=scores,
            source_language=source_language,
            target_language=target_language,
        )

    return _seed_scores


@pytest_asyncio.fixture
def seed_detail(neon_backend: NeonBackend) -> Callable[..., Awaitable[None]]:
    """Factory fixture for persisting detailed-word rows."""

    async def _seed_detail(
        source_word_id: int,
        word_type: PartOfSpeech,
        schema_key: str,
        schema_version: int,
        payload: dict[str, str | int | float | bool],
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
    ) -> None:
        return await seed_detail_row(
            backend=neon_backend,
            source_word_id=source_word_id,
            word_type=word_type,
            schema_key=schema_key,
            schema_version=schema_version,
            payload=payload,
            source_language=source_language,
            target_language=target_language,
        )

    return _seed_detail
