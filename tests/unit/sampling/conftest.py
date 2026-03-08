"""Shared fixtures for WordSampler unit tests — mock store and test data helpers."""

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.models import ScoredWordPair, WordPair
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
    source_word_id: int = 1,
) -> ScoredWordPair:
    """Create a ScoredWordPair with minimal boilerplate."""
    source = Word(normalized_form=source_form, word_type=word_type, language=Language.NL)
    target = Word(normalized_form=target_form, word_type=word_type, language=Language.RU)
    return ScoredWordPair(
        pair=WordPair(source=source, target=target), scores=scores or {}, source_word_id=source_word_id
    )


def make_word(
    normalized_form: str,
    word_type: PartOfSpeech = PartOfSpeech.NOUN,
    language: Language = Language.NL,
) -> Word:
    """Create a Word with minimal boilerplate."""
    return Word(normalized_form=normalized_form, word_type=word_type, language=language)


@pytest.fixture
def sampler(monkeypatch: pytest.MonkeyPatch) -> WordSampler:
    """Create a WordSampler with a dummy DATABASE_URL and default settings."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
    ws = WordSampler(user_id="u1", exercise_types=["flashcard"])
    return ws


@pytest.fixture
def sampler_injected() -> WordSampler:
    """Create a WordSampler with an injected mock store (no DATABASE_URL needed)."""
    mock_store = MockProgressStore([])
    return WordSampler(
        user_id="u1",
        exercise_types=["flashcard"],
        scored_store=mock_store,
    )


def patch_store(sampler: WordSampler, scored_pairs: list[ScoredWordPair]) -> None:
    """Replace the sampler's progress store with a mock returning the given pairs."""
    sampler._progress_store = MockProgressStore(scored_pairs)
