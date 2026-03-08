"""E2E tests: full cache lifecycle with real Neon DB and file-based SQLite."""

from pathlib import Path
from uuid import uuid4

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.service import DatabaseService
from tests.e2e.database.conftest import wait_for_translations
from tests.e2e.database_cache.conftest import WORDS, make_cache_service


async def _seed(user_id: str) -> None:
    """Add words to Neon and wait for translations."""
    service = DatabaseService(user_id=user_id)
    await service.add_words(WORDS)
    await wait_for_translations(len(WORDS))


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_full_lifecycle_init_read_write_flush(tmp_path: Path) -> None:
    """Init -> read -> write -> flush: complete cache round-trip against real Neon."""
    user_id = f"e2e_cache_{uuid4()}"
    await _seed(user_id)
    cache = make_cache_service(user_id, tmp_path)

    # 1. init -- bootstraps refresh from Neon
    status = await cache.init()
    assert status.is_ready is True
    assert status.has_snapshot is True

    # 2. get_words -- returns translated pairs
    pairs = await cache.get_words()
    source_forms = {p.source.normalized_form for p in pairs}
    expected_forms = {w.normalized_form for w in WORDS}
    assert source_forms == expected_forms

    # 3. get_word_pairs_with_scores -- all scores 0 for new words
    scored = await cache.get_word_pairs_with_scores()
    assert len(scored) == len(WORDS)
    for sp in scored:
        assert sp.scores["flashcard"] == 0

    # 4. record_exercise_result +1 for "tafel"
    await cache.record_exercise_result(
        source_word=Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL),
        exercise_type="flashcard",
        delta=1,
    )

    # 5. local score updated
    scored_after = await cache.get_word_pairs_with_scores()
    scores_by_form = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored_after}
    assert scores_by_form["tafel"] == 1
    assert scores_by_form["stoel"] == 0
    assert scores_by_form["lamp"] == 0

    # 6. flush -- replay events to Neon
    await cache.flush()
    status_after_flush = await cache.get_status()
    assert status_after_flush.pending_events == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_idempotent_flush(tmp_path: Path) -> None:
    """Flushing twice has no side effects -- second flush is a no-op."""
    user_id = f"e2e_cache_{uuid4()}"
    await _seed(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    await cache.record_exercise_result(
        source_word=Word(normalized_form="stoel", word_type=PartOfSpeech.NOUN, language=Language.NL),
        exercise_type="flashcard",
        delta=1,
    )

    # First flush
    await cache.flush()
    status_1 = await cache.get_status()
    assert status_1.pending_events == 0

    scored_after_first = await cache.get_word_pairs_with_scores()
    scores_1 = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored_after_first}

    # Second flush -- no-op
    await cache.flush()
    status_2 = await cache.get_status()
    assert status_2.pending_events == 0

    scored_after_second = await cache.get_word_pairs_with_scores()
    scores_2 = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored_after_second}

    assert scores_1 == scores_2
    assert scores_2["stoel"] == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_refresh_after_flush_restores_remote_state(tmp_path: Path) -> None:
    """After flush + refresh, scores match what was flushed (not doubled)."""
    user_id = f"e2e_cache_{uuid4()}"
    await _seed(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    await cache.record_exercise_result(
        source_word=Word(normalized_form="lamp", word_type=PartOfSpeech.NOUN, language=Language.NL),
        exercise_type="flashcard",
        delta=1,
    )

    await cache.flush()

    # Refresh -- re-download snapshot from Neon
    await cache.refresh()

    scored = await cache.get_word_pairs_with_scores()
    scores_by_form = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored}

    # Score must be exactly 1 (flushed value), not doubled
    assert scores_by_form["lamp"] == 1
    assert scores_by_form["tafel"] == 0
    assert scores_by_form["stoel"] == 0
