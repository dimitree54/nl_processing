"""Unit tests for ExerciseProgressStore."""

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.exceptions import ConfigurationError, DatabaseError
from nl_processing.database.exercise_progress import ExerciseProgressStore
from tests.unit.database.conftest import MockBackend

_HUIS = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
_LOPEN = Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL)


async def _seed_word_pair(backend: MockBackend) -> None:
    """Insert huis→HUIS word pair with user association and translation link."""
    src_id = await backend.add_word("nl", "huis", "noun")
    tgt_id = await backend.add_word("ru", "HUIS", "noun")
    assert src_id is not None
    assert tgt_id is not None
    await backend.add_user_word("u1", src_id, "nl")
    await backend.add_translation_link("nl_ru", src_id, tgt_id)


# ---- increment ----


@pytest.mark.asyncio
async def test_increment_positive(progress_store: ExerciseProgressStore, mock_backend: MockBackend) -> None:
    """delta=+1 increments score."""
    await _seed_word_pair(mock_backend)
    await progress_store.increment(_HUIS, "flashcard", delta=1)
    key = ("nl_ru", "u1", 1, "flashcard")
    assert mock_backend._scores[key] == 1


@pytest.mark.asyncio
async def test_increment_negative(progress_store: ExerciseProgressStore, mock_backend: MockBackend) -> None:
    """delta=-1 decrements score."""
    await _seed_word_pair(mock_backend)
    await progress_store.increment(_HUIS, "flashcard", delta=1)
    await progress_store.increment(_HUIS, "flashcard", delta=-1)
    key = ("nl_ru", "u1", 1, "flashcard")
    assert mock_backend._scores[key] == 0


@pytest.mark.asyncio
async def test_increment_delta_zero_raises(progress_store: ExerciseProgressStore) -> None:
    """delta=0 raises ValueError."""
    with pytest.raises(ValueError, match="delta must be"):
        await progress_store.increment(_HUIS, "flashcard", delta=0)


@pytest.mark.asyncio
async def test_increment_delta_two_raises(progress_store: ExerciseProgressStore) -> None:
    """delta=2 raises ValueError."""
    with pytest.raises(ValueError, match="delta must be"):
        await progress_store.increment(_HUIS, "flashcard", delta=2)


@pytest.mark.asyncio
async def test_increment_missing_word_raises(progress_store: ExerciseProgressStore) -> None:
    """Non-existent word raises DatabaseError."""
    missing = Word(normalized_form="onbekend", word_type=PartOfSpeech.NOUN, language=Language.NL)
    with pytest.raises(DatabaseError, match="not found"):
        await progress_store.increment(missing, "flashcard", delta=1)


# ---- get_word_pairs_with_scores ----


@pytest.mark.asyncio
async def test_get_scored_pairs(progress_store: ExerciseProgressStore, mock_backend: MockBackend) -> None:
    """Returns ScoredWordPair with correct scores."""
    await _seed_word_pair(mock_backend)
    await progress_store.increment(_HUIS, "flashcard", delta=1)
    await progress_store.increment(_HUIS, "flashcard", delta=1)
    scored = await progress_store.get_word_pairs_with_scores(["flashcard"])
    assert len(scored) == 1
    assert scored[0].scores["flashcard"] == 2
    assert scored[0].pair.source.normalized_form == "huis"


@pytest.mark.asyncio
async def test_missing_scores_default_zero(progress_store: ExerciseProgressStore, mock_backend: MockBackend) -> None:
    """Words without scores get default 0."""
    await _seed_word_pair(mock_backend)
    scored = await progress_store.get_word_pairs_with_scores(["flashcard"])
    assert len(scored) == 1
    assert scored[0].scores["flashcard"] == 0


@pytest.mark.asyncio
async def test_empty_exercise_types(progress_store: ExerciseProgressStore, mock_backend: MockBackend) -> None:
    """Empty exercise_types → empty scores dict."""
    await _seed_word_pair(mock_backend)
    scored = await progress_store.get_word_pairs_with_scores([])
    assert len(scored) == 1
    assert scored[0].scores == {}


# ---- constructor ----


def test_constructor_raises_without_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """ConfigurationError raised when DATABASE_URL not set."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError):
        ExerciseProgressStore(user_id="u1", source_language=Language.NL, target_language=Language.RU)
