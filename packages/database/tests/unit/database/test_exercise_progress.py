"""Unit tests for ExerciseProgressStore."""

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPairSnapshot
import pytest

from nl_processing.database.exceptions import ConfigurationError
from nl_processing.database.exercise_progress import ExerciseProgressStore
from tests.unit.database.conftest import MockBackend

_HUIS = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)


async def _seed_word_pair(backend: MockBackend) -> None:
    """Insert huis->HUIS word pair with user association and translation link."""
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
    await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=1)
    key = ("nl_ru_flashcard", "u1", 1)
    assert mock_backend._scores[key] == 1


@pytest.mark.asyncio
async def test_increment_negative(progress_store: ExerciseProgressStore, mock_backend: MockBackend) -> None:
    """delta=-1 decrements score."""
    await _seed_word_pair(mock_backend)
    await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=1)
    await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=-1)
    key = ("nl_ru_flashcard", "u1", 1)
    assert mock_backend._scores[key] == 0


@pytest.mark.asyncio
async def test_increment_delta_zero_raises(progress_store: ExerciseProgressStore) -> None:
    """delta=0 raises ValueError."""
    with pytest.raises(ValueError, match="delta must be"):
        await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=0)


@pytest.mark.asyncio
async def test_increment_delta_two_raises(progress_store: ExerciseProgressStore) -> None:
    """delta=2 raises ValueError."""
    with pytest.raises(ValueError, match="delta must be"):
        await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=2)


@pytest.mark.asyncio
async def test_increment_unknown_exercise_type_raises(progress_store: ExerciseProgressStore) -> None:
    """Unknown exercise_type raises ValueError."""
    with pytest.raises(ValueError, match="Unknown exercise_type"):
        await progress_store.increment(source_word_id=1, exercise_type="typing", delta=1)


# ---- get_word_pairs_with_scores ----


@pytest.mark.asyncio
async def test_get_scored_pairs(progress_store: ExerciseProgressStore, mock_backend: MockBackend) -> None:
    """Returns ScoredWordPair with correct scores."""
    await _seed_word_pair(mock_backend)
    await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=1)
    await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=1)
    scored = await progress_store.get_word_pairs_with_scores()
    assert len(scored) == 1
    assert scored[0].scores["flashcard"] == 2
    assert scored[0].pair.source.normalized_form == "huis"
    assert scored[0].source_word_id == 1


@pytest.mark.asyncio
async def test_missing_scores_default_zero(progress_store: ExerciseProgressStore, mock_backend: MockBackend) -> None:
    """Words without scores get default 0."""
    await _seed_word_pair(mock_backend)
    scored = await progress_store.get_word_pairs_with_scores()
    assert len(scored) == 1
    assert scored[0].scores["flashcard"] == 0


def test_empty_exercise_types_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty exercise_types in constructor raises ValueError."""
    monkeypatch.setenv("DATABASE_URL", "mock://test")
    with pytest.raises(ValueError, match="exercise_types must be a non-empty list"):
        ExerciseProgressStore(
            user_id="u1",
            source_language=Language.NL,
            target_language=Language.RU,
            exercise_types=[],
        )


# ---- apply_score_delta idempotency ----


@pytest.mark.asyncio
async def test_apply_score_delta_applies_once(
    progress_store: ExerciseProgressStore,
    mock_backend: MockBackend,
) -> None:
    """apply_score_delta applies a delta exactly once for a given event_id."""
    await _seed_word_pair(mock_backend)
    await progress_store.apply_score_delta("evt-1", 1, "flashcard", 1)
    await progress_store.apply_score_delta("evt-1", 1, "flashcard", 1)
    key = ("nl_ru_flashcard", "u1", 1)
    assert mock_backend._scores[key] == 1


@pytest.mark.asyncio
async def test_apply_score_delta_rejects_zero(progress_store: ExerciseProgressStore) -> None:
    """apply_score_delta raises ValueError when delta is 0."""
    with pytest.raises(ValueError, match="delta must be"):
        await progress_store.apply_score_delta("evt-zero", 1, "flashcard", 0)


@pytest.mark.asyncio
async def test_apply_score_delta_rejects_two(progress_store: ExerciseProgressStore) -> None:
    """apply_score_delta raises ValueError when delta is 2."""
    with pytest.raises(ValueError, match="delta must be"):
        await progress_store.apply_score_delta("evt-two", 1, "flashcard", 2)


# ---- export_remote_snapshot ----


@pytest.mark.asyncio
async def test_export_remote_snapshot(
    progress_store: ExerciseProgressStore,
    mock_backend: MockBackend,
) -> None:
    """export_remote_snapshot returns cache-ready snapshots with stable IDs."""
    await _seed_word_pair(mock_backend)
    snapshot = await progress_store.export_remote_snapshot()
    assert len(snapshot) == 1
    assert isinstance(snapshot[0], WordPairSnapshot)
    assert snapshot[0].scores["flashcard"] == 0
    assert snapshot[0].source_word_id == 1
    assert snapshot[0].target_word_id == 1


# ---- constructor ----


def test_constructor_raises_without_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """ConfigurationError raised when DATABASE_URL not set."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError):
        ExerciseProgressStore(
            user_id="u1",
            source_language=Language.NL,
            target_language=Language.RU,
            exercise_types=["flashcard"],
        )
