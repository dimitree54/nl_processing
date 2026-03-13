from pydantic import ValidationError
import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.core.tiered_models import TieredProgressSummary, TieredSnapshotEntry


def test_tiered_progress_summary_instantiation() -> None:
    """Test TieredProgressSummary can be created and accessed."""
    summary = TieredProgressSummary(
        total_words=100,
        fully_completed_words=25,
        completion_ratio=0.25,
    )

    assert summary.total_words == 100
    assert summary.fully_completed_words == 25
    assert summary.completion_ratio == 0.25


def test_tiered_progress_summary_boundary_values() -> None:
    """Test TieredProgressSummary with boundary values."""
    empty_summary = TieredProgressSummary(
        total_words=0,
        fully_completed_words=0,
        completion_ratio=0.0,
    )
    assert empty_summary.total_words == 0
    assert empty_summary.fully_completed_words == 0
    assert empty_summary.completion_ratio == 0.0

    full_summary = TieredProgressSummary(
        total_words=50,
        fully_completed_words=50,
        completion_ratio=1.0,
    )
    assert full_summary.total_words == 50
    assert full_summary.fully_completed_words == 50
    assert full_summary.completion_ratio == 1.0


def test_tiered_progress_summary_serialization() -> None:
    """Test TieredProgressSummary serialization via model_dump."""
    summary = TieredProgressSummary(
        total_words=200,
        fully_completed_words=75,
        completion_ratio=0.375,
    )
    data = summary.model_dump()

    assert data == {
        "total_words": 200,
        "fully_completed_words": 75,
        "completion_ratio": 0.375,
    }


def test_tiered_progress_summary_missing_fields() -> None:
    """Test TieredProgressSummary raises ValidationError on missing fields."""
    with pytest.raises(ValidationError):
        TieredProgressSummary(total_words=100, fully_completed_words=25)

    with pytest.raises(ValidationError):
        TieredProgressSummary(total_words=100)

    with pytest.raises(ValidationError):
        TieredProgressSummary()


def test_tiered_snapshot_entry_instantiation() -> None:
    """Test TieredSnapshotEntry can be created and accessed."""
    word_pair = WordPair(
        source=Word(normalized_form="snel", word_type=PartOfSpeech.ADVERB, language=Language.NL),
        target=Word(normalized_form="fast", word_type=PartOfSpeech.ADVERB, language=Language.RU),
    )
    entry = TieredSnapshotEntry(
        source_word_id=10,
        target_word_id=20,
        pair=word_pair,
        scores={"translate": 3, "multiple_choice": 2, "listening": 1},
        in_repeat_mode=False,
    )

    assert entry.source_word_id == 10
    assert entry.target_word_id == 20
    assert entry.pair == word_pair
    assert entry.scores == {"translate": 3, "multiple_choice": 2, "listening": 1}
    assert entry.in_repeat_mode is False


def test_tiered_snapshot_entry_serialization() -> None:
    """Test TieredSnapshotEntry serialization via model_dump."""
    word_pair = WordPair(
        source=Word(normalized_form="mooi", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        target=Word(normalized_form="beautiful", word_type=PartOfSpeech.ADJECTIVE, language=Language.RU),
    )
    entry = TieredSnapshotEntry(
        source_word_id=101,
        target_word_id=202,
        pair=word_pair,
        scores={"listening": 0, "translate": 1},
        in_repeat_mode=True,
    )
    data = entry.model_dump()

    assert data["source_word_id"] == 101
    assert data["target_word_id"] == 202
    assert data["scores"] == {"listening": 0, "translate": 1}
    assert data["in_repeat_mode"] is True


def test_tiered_snapshot_entry_missing_fields() -> None:
    """Test TieredSnapshotEntry raises ValidationError on missing fields."""
    word_pair = WordPair(
        source=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.NL),
        target=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.RU),
    )

    with pytest.raises(ValidationError):
        TieredSnapshotEntry(source_word_id=1, target_word_id=2, pair=word_pair, scores={})

    with pytest.raises(ValidationError):
        TieredSnapshotEntry(source_word_id=1, target_word_id=2, scores={})

    with pytest.raises(ValidationError):
        TieredSnapshotEntry()
