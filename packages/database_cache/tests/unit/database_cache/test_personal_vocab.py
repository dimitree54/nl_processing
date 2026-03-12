"""Unit tests for personal vocabulary features in DatabaseCacheService."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from nl_processing.core.models import Language
from nl_processing.database.models import ExerciseProgressSummary, PersonalWord
import pytest

from nl_processing.database_cache.exceptions import CacheNotReadyError
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.service import DatabaseCacheService
from tests.unit.database_cache.conftest import MockProgressStore, MockRemoteDelete, make_scored_pair


@pytest.mark.asyncio
async def test_list_personal_words_before_init_raises() -> None:
    """Calling list_personal_words before init() raises CacheNotReadyError."""
    svc = DatabaseCacheService(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
    )
    with pytest.raises(CacheNotReadyError):
        await svc.list_personal_words()


@pytest.mark.asyncio
async def test_list_personal_words_returns_personal_word_objects(cache_service: DatabaseCacheService) -> None:
    """list_personal_words returns a list of PersonalWord objects."""
    result = await cache_service.list_personal_words()
    assert len(result) == 2
    assert all(isinstance(pw, PersonalWord) for pw in result)
    forms = {pw.pair.source.normalized_form for pw in result}
    assert forms == {"huis", "boek"}


@pytest.mark.asyncio
async def test_list_personal_words_includes_all_fields(cache_service: DatabaseCacheService) -> None:
    """list_personal_words includes added_at, scores, and stable IDs."""
    result = await cache_service.list_personal_words()
    assert len(result) == 2
    for pw in result:
        # Check added_at
        assert pw.added_at is not None
        assert isinstance(pw.added_at, datetime)
        # Check scores
        assert "flashcard" in pw.scores
        assert pw.scores["flashcard"] == 0  # From conftest fixture
        # Check stable IDs
        assert isinstance(pw.source_word_id, int)
        assert isinstance(pw.target_word_id, int)
        assert pw.source_word_id > 0
        assert pw.target_word_id > 0


@pytest.mark.asyncio
async def test_get_progress_summary_before_init_raises() -> None:
    """Calling get_progress_summary before init() raises CacheNotReadyError."""
    svc = DatabaseCacheService(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
    )
    with pytest.raises(CacheNotReadyError):
        await svc.get_progress_summary()


@pytest.mark.asyncio
async def test_get_progress_summary_all_zero(cache_service: DatabaseCacheService) -> None:
    """get_progress_summary with 2 words both at score 0 returns correct stats."""
    result = await cache_service.get_progress_summary()

    assert "flashcard" in result
    summary = result["flashcard"]
    assert isinstance(summary, ExerciseProgressSummary)
    assert summary.total_words == 2
    assert summary.negative_words == 0
    assert summary.negative_ratio == 0.0
    assert summary.negative_percentage == 0.0


@pytest.mark.asyncio
async def test_get_progress_summary_with_negative_scores(tmp_path: Path) -> None:
    """get_progress_summary with 1 negative score out of 2 returns correct stats."""
    local_store = LocalStore(str(tmp_path / "test.db"))
    svc = DatabaseCacheService(
        user_id="test_user",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
        cache_dir=str(tmp_path),
        remote_progress=MockProgressStore(
            snapshot=[
                make_scored_pair("huis", "dom", 1, {"flashcard": -1}),  # Negative score
                make_scored_pair("boek", "kniga", 2, {"flashcard": 0}),  # Zero score
            ]
        ),
        remote_db=MockRemoteDelete(),
        local_store=local_store,
    )
    await svc.init()

    result = await svc.get_progress_summary()

    assert "flashcard" in result
    summary = result["flashcard"]
    assert summary.total_words == 2
    assert summary.negative_words == 1
    assert summary.negative_ratio == 0.5
    assert summary.negative_percentage == 50.0

    await asyncio.sleep(0)
    await local_store.close()


@pytest.mark.asyncio
async def test_get_progress_summary_empty_cache(tmp_path: Path) -> None:
    """get_progress_summary with empty cache returns all zeros."""
    local_store = LocalStore(str(tmp_path / "test.db"))
    svc = DatabaseCacheService(
        user_id="test_user",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
        cache_dir=str(tmp_path),
        remote_progress=MockProgressStore(snapshot=[]),
        remote_db=MockRemoteDelete(),
        local_store=local_store,
    )
    await svc.init()

    result = await svc.get_progress_summary()

    assert "flashcard" in result
    summary = result["flashcard"]
    assert summary.total_words == 0
    assert summary.negative_words == 0
    assert summary.negative_ratio == 0.0
    assert summary.negative_percentage == 0.0

    await asyncio.sleep(0)
    await local_store.close()


@pytest.mark.asyncio
async def test_get_progress_summary_matches_list_personal_words_count(cache_service: DatabaseCacheService) -> None:
    """DEC-7: get_progress_summary total_words matches len(list_personal_words())."""
    personal_words = await cache_service.list_personal_words()
    progress_summary = await cache_service.get_progress_summary()

    expected_count = len(personal_words)
    actual_count = progress_summary["flashcard"].total_words

    assert actual_count == expected_count
    assert expected_count == 2  # From conftest fixture
