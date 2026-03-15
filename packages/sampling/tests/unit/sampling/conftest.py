"""Shared fixtures for WordSampler unit tests."""

from nl_processing.core.models import Language, PartOfSpeech, ScoredWordPair, Word, WordPair
import pytest

from nl_processing.sampling.service import WordSampler


class MockProgressStore:
    """In-memory progress store returning configurable scored word pairs."""

    def __init__(self, scored_pairs: list[ScoredWordPair]) -> None:
        self._scored_pairs = scored_pairs

    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]:
        return self._scored_pairs


def make_scored_pair(
    source_form: str,
    target_form: str,
    word_type: PartOfSpeech = PartOfSpeech.NOUN,
    scores: dict[str, int] | None = None,
) -> ScoredWordPair:
    """Create a ScoredWordPair with minimal boilerplate."""
    source = Word(normalized_form=source_form, word_type=word_type, language=Language.NL)
    target = Word(normalized_form=target_form, word_type=word_type, language=Language.RU)
    return ScoredWordPair(
        pair=WordPair(source=source, target=target),
        scores=scores or {},
    )


def make_word(
    normalized_form: str,
    word_type: PartOfSpeech = PartOfSpeech.NOUN,
    language: Language = Language.NL,
) -> Word:
    """Create a Word with minimal boilerplate."""
    return Word(normalized_form=normalized_form, word_type=word_type, language=language)


@pytest.fixture
def sampler() -> WordSampler:
    """Create a WordSampler with an injected mock store."""
    return WordSampler(
        scored_store=MockProgressStore([]),
        exercise_type="flashcard",
    )


def patch_store(sampler: WordSampler, scored_pairs: list[ScoredWordPair]) -> None:
    """Replace the sampler's progress store with a mock returning the given pairs."""
    sampler._progress_store = MockProgressStore(scored_pairs)
