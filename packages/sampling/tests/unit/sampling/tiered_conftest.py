"""Shared helpers for TieredMultiExerciseSampler unit tests."""

from nl_processing.core.models import ScoredWordPair
from nl_processing.core.protocols import ScoredPairProvider

from nl_processing.sampling.service import TieredMultiExerciseSampler
from tests.unit.sampling.conftest import MockProgressStore, make_scored_pair


def make_tiered_candidate(
    source_form: str,
    target_form: str,
    scores: dict[str, int] | None = None,
) -> ScoredWordPair:
    """Create a scored pair for tiered sampler tests."""
    return make_scored_pair(source_form, target_form, scores=scores)


def create_tiered_sampler(
    scored_pairs: list[ScoredWordPair],
    *,
    exercise_types: list[str] | None = None,
    tiered_exercise_type: str = "flashcard",
    finished_exercise_weight: float = 0.01,
) -> TieredMultiExerciseSampler:
    """Create a TieredMultiExerciseSampler with an injected mock store."""
    return TieredMultiExerciseSampler(
        scored_store=MockProgressStore(scored_pairs),
        exercise_types=exercise_types if exercise_types is not None else ["flashcard"],
        tiered_exercise_type=tiered_exercise_type,
        finished_exercise_weight=finished_exercise_weight,
    )


def mock_provider_satisfies_protocol() -> bool:
    """MockProgressStore structurally satisfies ScoredPairProvider."""
    return isinstance(MockProgressStore([]), ScoredPairProvider)
