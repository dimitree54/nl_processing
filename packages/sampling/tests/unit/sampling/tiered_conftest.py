"""Shared fixtures for TieredExerciseSampler unit tests — mock store and test data helpers."""

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.core.tiered_models import TieredCandidate
from nl_processing.core.tiered_ports import TieredCandidateProvider


class MockTieredCandidateProvider:
    """In-memory tiered candidate provider returning configurable candidates."""

    def __init__(self, candidates: list[TieredCandidate]) -> None:
        self._candidates = candidates

    async def get_tiered_candidates(self) -> list[TieredCandidate]:
        return self._candidates


def make_tiered_candidate(
    source_form: str,
    target_form: str,
    scores: dict[str, int] | None = None,
    in_repeat_mode: bool = False,
    source_word_id: int = 1,
    word_type: PartOfSpeech = PartOfSpeech.NOUN,
) -> TieredCandidate:
    """Create a TieredCandidate with minimal boilerplate."""
    source = Word(normalized_form=source_form, word_type=word_type, language=Language.NL)
    target = Word(normalized_form=target_form, word_type=word_type, language=Language.RU)
    pair = WordPair(source=source, target=target)
    return TieredCandidate(
        pair=pair,
        source_word_id=source_word_id,
        scores=scores or {},
        in_repeat_mode=in_repeat_mode,
    )


def mock_provider_satisfies_protocol() -> bool:
    """Test that MockTieredCandidateProvider structurally satisfies TieredCandidateProvider."""
    mock = MockTieredCandidateProvider([])
    return isinstance(mock, TieredCandidateProvider)
