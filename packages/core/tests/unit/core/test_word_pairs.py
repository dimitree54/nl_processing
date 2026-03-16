from datetime import UTC, datetime

from pydantic import ValidationError
import pytest

from nl_processing.core.models import Language, PartOfSpeech, ScoredWordPair, Word, WordPair, WordPairSnapshot


def test_word_pair_instantiation() -> None:
    """Test WordPair can be created and accessed."""
    source = Word(normalized_form="fiets", word_type=PartOfSpeech.NOUN, language=Language.NL)
    target = Word(normalized_form="велосипед", word_type=PartOfSpeech.NOUN, language=Language.RU)

    pair = WordPair(source=source, target=target)

    assert pair.source == source
    assert pair.target == target


def test_word_pair_serialization() -> None:
    """Test WordPair serialization via model_dump."""
    pair = WordPair(
        source=Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        target=Word(normalized_form="бежать", word_type=PartOfSpeech.VERB, language=Language.RU),
    )

    assert pair.model_dump(mode="json") == {
        "source": {"normalized_form": "lopen", "word_type": "verb", "language": "nl"},
        "target": {"normalized_form": "бежать", "word_type": "verb", "language": "ru"},
    }


def test_scored_word_pair_instantiation() -> None:
    """Test ScoredWordPair can be created and accessed."""
    pair = WordPair(
        source=Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
        target=Word(normalized_form="дом", word_type=PartOfSpeech.NOUN, language=Language.RU),
    )

    scored_pair = ScoredWordPair(
        pair=pair,
        scores={"reading": 3, "writing": 5},
    )

    assert scored_pair.pair == pair
    assert scored_pair.scores == {"reading": 3, "writing": 5}


def test_scored_word_pair_missing_fields() -> None:
    """Test ScoredWordPair raises ValidationError on missing fields."""
    pair = WordPair(
        source=Word(normalized_form="zien", word_type=PartOfSpeech.VERB, language=Language.NL),
        target=Word(normalized_form="видеть", word_type=PartOfSpeech.VERB, language=Language.RU),
    )

    with pytest.raises(ValidationError):
        ScoredWordPair(scores={"reading": 1})

    with pytest.raises(ValidationError):
        ScoredWordPair(pair=pair)


def test_word_pair_snapshot_instantiation() -> None:
    """Test WordPairSnapshot extends scored pairs with stable ids and required added_at."""

    pair = WordPair(
        source=Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
        target=Word(normalized_form="книга", word_type=PartOfSpeech.NOUN, language=Language.RU),
    )

    now = datetime.now(tz=UTC)
    snapshot = WordPairSnapshot(
        pair=pair,
        scores={"reading": 2},
        source_word_id=11,
        target_word_id=22,
        added_at=now,
    )

    assert snapshot.pair == pair
    assert snapshot.scores == {"reading": 2}
    assert snapshot.source_word_id == 11
    assert snapshot.target_word_id == 22
    assert snapshot.added_at == now


def test_word_pair_snapshot_missing_fields() -> None:
    """Test WordPairSnapshot raises ValidationError on missing fields."""
    pair = WordPair(
        source=Word(normalized_form="zien", word_type=PartOfSpeech.VERB, language=Language.NL),
        target=Word(normalized_form="видеть", word_type=PartOfSpeech.VERB, language=Language.RU),
    )

    with pytest.raises(ValidationError):
        WordPairSnapshot(scores={"reading": 1}, source_word_id=1, target_word_id=2)

    with pytest.raises(ValidationError):
        WordPairSnapshot(pair=pair, source_word_id=1, target_word_id=2)

    with pytest.raises(ValidationError):
        WordPairSnapshot(pair=pair, scores={"reading": 1}, target_word_id=2)

    with pytest.raises(ValidationError):
        WordPairSnapshot(pair=pair, scores={"reading": 1}, source_word_id=1)
