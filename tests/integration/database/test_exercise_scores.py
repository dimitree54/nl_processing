"""Integration tests for exercise score operations against real Neon PostgreSQL."""

import uuid

import pytest

from nl_processing.database.backend.neon import NeonBackend


def _uid() -> str:
    """Generate a unique user_id to avoid pytest-xdist conflicts."""
    return f"test_user_{uuid.uuid4().hex[:12]}"


async def _insert_word(backend: NeonBackend) -> int:
    """Insert a unique word into words_nl and return its id."""
    word = f"score_word_{uuid.uuid4().hex[:8]}"
    word_id = await backend.add_word("nl", word, "noun")
    assert word_id is not None
    return word_id


@pytest.mark.asyncio
async def test_increment_creates_new_score(neon_backend: NeonBackend) -> None:
    """increment_user_exercise_score creates a new score row (upsert)."""
    user_id = _uid()
    word_id = await _insert_word(neon_backend)

    score = await neon_backend.increment_user_exercise_score(
        "nl_ru_flashcard",
        user_id,
        word_id,
        1,
    )
    assert score == 1


@pytest.mark.asyncio
async def test_increment_updates_existing_score(neon_backend: NeonBackend) -> None:
    """increment_user_exercise_score updates an existing score."""
    user_id = _uid()
    word_id = await _insert_word(neon_backend)

    await neon_backend.increment_user_exercise_score("nl_ru_flashcard", user_id, word_id, 1)
    score = await neon_backend.increment_user_exercise_score(
        "nl_ru_flashcard",
        user_id,
        word_id,
        1,
    )
    assert score == 2


@pytest.mark.asyncio
async def test_score_increments_correctly(neon_backend: NeonBackend) -> None:
    """Score starts at delta value and increments with subsequent calls."""
    user_id = _uid()
    word_id = await _insert_word(neon_backend)

    score1 = await neon_backend.increment_user_exercise_score(
        "nl_ru_flashcard",
        user_id,
        word_id,
        1,
    )
    assert score1 == 1

    score2 = await neon_backend.increment_user_exercise_score(
        "nl_ru_flashcard",
        user_id,
        word_id,
        1,
    )
    assert score2 == 2

    score3 = await neon_backend.increment_user_exercise_score(
        "nl_ru_flashcard",
        user_id,
        word_id,
        1,
    )
    assert score3 == 3


@pytest.mark.asyncio
async def test_score_decrements_correctly(neon_backend: NeonBackend) -> None:
    """Score decrements with delta=-1."""
    user_id = _uid()
    word_id = await _insert_word(neon_backend)

    await neon_backend.increment_user_exercise_score("nl_ru_flashcard", user_id, word_id, 1)
    await neon_backend.increment_user_exercise_score("nl_ru_flashcard", user_id, word_id, 1)

    score = await neon_backend.increment_user_exercise_score(
        "nl_ru_flashcard",
        user_id,
        word_id,
        -1,
    )
    assert score == 1


@pytest.mark.asyncio
async def test_get_user_exercise_scores_returns_correct_scores(neon_backend: NeonBackend) -> None:
    """get_user_exercise_scores returns correct score for a per-exercise table."""
    user_id = _uid()
    word_id = await _insert_word(neon_backend)

    await neon_backend.increment_user_exercise_score("nl_ru_flashcard", user_id, word_id, 1)
    await neon_backend.increment_user_exercise_score("nl_ru_flashcard", user_id, word_id, 1)

    scores = await neon_backend.get_user_exercise_scores(
        "nl_ru_flashcard",
        user_id,
        [word_id],
    )
    assert len(scores) == 1
    assert int(scores[0]["score"]) == 2


@pytest.mark.asyncio
async def test_get_user_exercise_scores_empty_returns_empty(neon_backend: NeonBackend) -> None:
    """get_user_exercise_scores returns empty list when no scores exist."""
    user_id = _uid()

    scores = await neon_backend.get_user_exercise_scores(
        "nl_ru_flashcard",
        user_id,
        [99999],
    )
    assert scores == []


@pytest.mark.asyncio
async def test_get_user_exercise_scores_empty_word_ids(neon_backend: NeonBackend) -> None:
    """get_user_exercise_scores returns empty list for empty word_ids."""
    user_id = _uid()

    assert await neon_backend.get_user_exercise_scores("nl_ru_flashcard", user_id, []) == []
