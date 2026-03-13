from pydantic import ValidationError
import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.core.tiered_models import TieredCandidate, TieredExerciseSelection


def test_tiered_candidate_instantiation() -> None:
    """Test TieredCandidate can be created and accessed."""
    word_pair = WordPair(
        source=Word(normalized_form="de fiets", word_type=PartOfSpeech.NOUN, language=Language.NL),
        target=Word(normalized_form="bicycle", word_type=PartOfSpeech.NOUN, language=Language.RU),
    )
    candidate = TieredCandidate(
        pair=word_pair,
        source_word_id=42,
        scores={"multiple_choice": 2, "translate": 1},
        in_repeat_mode=False,
    )

    assert candidate.pair == word_pair
    assert candidate.source_word_id == 42
    assert candidate.scores == {"multiple_choice": 2, "translate": 1}
    assert candidate.in_repeat_mode is False


def test_tiered_candidate_serialization() -> None:
    """Test TieredCandidate serialization via model_dump."""
    word_pair = WordPair(
        source=Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        target=Word(normalized_form="walk", word_type=PartOfSpeech.VERB, language=Language.RU),
    )
    candidate = TieredCandidate(
        pair=word_pair,
        source_word_id=123,
        scores={"listening": 0},
        in_repeat_mode=True,
    )
    data = candidate.model_dump()

    assert data["source_word_id"] == 123
    assert data["scores"] == {"listening": 0}
    assert data["in_repeat_mode"] is True


def test_tiered_candidate_empty_scores() -> None:
    """Test TieredCandidate with empty scores dict is valid."""
    word_pair = WordPair(
        source=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.NL),
        target=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.RU),
    )
    candidate = TieredCandidate(
        pair=word_pair,
        source_word_id=1,
        scores={},
        in_repeat_mode=False,
    )

    assert candidate.scores == {}


def test_tiered_candidate_missing_fields() -> None:
    """Test TieredCandidate raises ValidationError on missing fields."""
    word_pair = WordPair(
        source=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.NL),
        target=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.RU),
    )

    with pytest.raises(ValidationError):
        TieredCandidate(pair=word_pair, source_word_id=1, scores={})

    with pytest.raises(ValidationError):
        TieredCandidate(pair=word_pair, in_repeat_mode=False)

    with pytest.raises(ValidationError):
        TieredCandidate()


def test_tiered_exercise_selection_instantiation() -> None:
    """Test TieredExerciseSelection can be created and accessed."""
    word_pair = WordPair(
        source=Word(normalized_form="de kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
        target=Word(normalized_form="cat", word_type=PartOfSpeech.NOUN, language=Language.RU),
    )
    selection = TieredExerciseSelection(
        pair=word_pair,
        source_word_id=55,
        exercise_type="multiple_choice",
        in_repeat_mode=True,
    )

    assert selection.pair == word_pair
    assert selection.source_word_id == 55
    assert selection.exercise_type == "multiple_choice"
    assert selection.in_repeat_mode is True


def test_tiered_exercise_selection_serialization() -> None:
    """Test TieredExerciseSelection serialization via model_dump."""
    word_pair = WordPair(
        source=Word(normalized_form="groen", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        target=Word(normalized_form="green", word_type=PartOfSpeech.ADJECTIVE, language=Language.RU),
    )
    selection = TieredExerciseSelection(
        pair=word_pair,
        source_word_id=99,
        exercise_type="listening",
        in_repeat_mode=False,
    )
    data = selection.model_dump()

    assert data["source_word_id"] == 99
    assert data["exercise_type"] == "listening"
    assert data["in_repeat_mode"] is False


def test_tiered_exercise_selection_missing_fields() -> None:
    """Test TieredExerciseSelection raises ValidationError on missing fields."""
    word_pair = WordPair(
        source=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.NL),
        target=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.RU),
    )

    with pytest.raises(ValidationError):
        TieredExerciseSelection(pair=word_pair, source_word_id=1, exercise_type="translate")

    with pytest.raises(ValidationError):
        TieredExerciseSelection(pair=word_pair, in_repeat_mode=False)

    with pytest.raises(ValidationError):
        TieredExerciseSelection()
