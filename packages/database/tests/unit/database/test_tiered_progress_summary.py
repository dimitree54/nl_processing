"""Unit tests for tiered progress summary computation."""

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.core.tiered_models import TieredCandidate

from nl_processing.database._tiered_helpers import compute_tiered_progress


class TestComputeTieredProgress:
    """Test tiered progress computation using all-positive completion rule TFR-DB-5."""

    def test_empty_candidates_returns_zero_progress(self) -> None:
        """Empty candidate list returns zero progress."""
        result = compute_tiered_progress([], ["flashcard", "typing"])
        assert result.total_words == 0
        assert result.fully_completed_words == 0
        assert result.completion_ratio == 0.0

    def test_all_candidates_fully_completed(self) -> None:
        """All candidates with all positive scores are fully completed."""
        candidates = [
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="hond", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="собака", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=1,
                scores={"flashcard": 2, "typing": 1},
                in_repeat_mode=False,
            ),
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="kat", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="кот", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=2,
                scores={"flashcard": 3, "typing": 2},
                in_repeat_mode=False,
            ),
        ]

        result = compute_tiered_progress(candidates, ["flashcard", "typing"])
        assert result.total_words == 2
        assert result.fully_completed_words == 2
        assert result.completion_ratio == 1.0

    def test_no_candidates_fully_completed(self) -> None:
        """No candidates with all positive scores means zero completion."""
        candidates = [
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="hond", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="собака", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=1,
                scores={"flashcard": 2, "typing": 0},  # typing not positive
                in_repeat_mode=False,
            ),
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="kat", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="кот", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=2,
                scores={"flashcard": 0, "typing": 2},  # flashcard not positive
                in_repeat_mode=False,
            ),
        ]

        result = compute_tiered_progress(candidates, ["flashcard", "typing"])
        assert result.total_words == 2
        assert result.fully_completed_words == 0
        assert result.completion_ratio == 0.0

    def test_mixed_completion_calculates_ratio(self) -> None:
        """Mixed completion levels calculate correct ratio."""
        candidates = [
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="hond", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="собака", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=1,
                scores={"flashcard": 2, "typing": 1},  # Fully completed
                in_repeat_mode=False,
            ),
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="kat", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="кот", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=2,
                scores={"flashcard": 0, "typing": 2},  # Not fully completed
                in_repeat_mode=False,
            ),
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="vis", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="рыба", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=3,
                scores={"flashcard": 1, "typing": 3},  # Fully completed
                in_repeat_mode=True,
            ),
        ]

        result = compute_tiered_progress(candidates, ["flashcard", "typing"])
        assert result.total_words == 3
        assert result.fully_completed_words == 2
        assert result.completion_ratio == 2.0 / 3.0

    def test_missing_scores_default_to_zero(self) -> None:
        """Missing scores in candidate.scores default to 0 per TBR-DB-2."""
        candidates = [
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="hond", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="собака", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=1,
                scores={"flashcard": 2},  # typing missing, defaults to 0
                in_repeat_mode=False,
            ),
        ]

        result = compute_tiered_progress(candidates, ["flashcard", "typing"])
        assert result.total_words == 1
        assert result.fully_completed_words == 0  # typing score is 0, not positive
        assert result.completion_ratio == 0.0

    def test_negative_scores_not_positive(self) -> None:
        """Negative scores are not considered positive."""
        candidates = [
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="hond", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="собака", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=1,
                scores={"flashcard": -1, "typing": 2},  # flashcard negative
                in_repeat_mode=True,
            ),
        ]

        result = compute_tiered_progress(candidates, ["flashcard", "typing"])
        assert result.total_words == 1
        assert result.fully_completed_words == 0  # flashcard is negative
        assert result.completion_ratio == 0.0

    def test_single_exercise_type(self) -> None:
        """Works correctly with single exercise type."""
        candidates = [
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="hond", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="собака", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=1,
                scores={"flashcard": 1},
                in_repeat_mode=False,
            ),
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="kat", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="кот", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=2,
                scores={"flashcard": 0},
                in_repeat_mode=False,
            ),
        ]

        result = compute_tiered_progress(candidates, ["flashcard"])
        assert result.total_words == 2
        assert result.fully_completed_words == 1  # Only first word has positive flashcard score
        assert result.completion_ratio == 0.5

    def test_repeat_mode_doesnt_affect_completion(self) -> None:
        """Repeat mode state doesn't affect completion calculation."""
        candidates = [
            TieredCandidate(
                pair=WordPair(
                    source=Word(normalized_form="hond", language=Language.NL, word_type=PartOfSpeech.NOUN),
                    target=Word(normalized_form="собака", language=Language.RU, word_type=PartOfSpeech.NOUN),
                ),
                source_word_id=1,
                scores={"flashcard": 1, "typing": 2},
                in_repeat_mode=True,  # In repeat mode but fully completed
            ),
        ]

        result = compute_tiered_progress(candidates, ["flashcard", "typing"])
        assert result.total_words == 1
        assert result.fully_completed_words == 1  # Completion only depends on scores
        assert result.completion_ratio == 1.0
