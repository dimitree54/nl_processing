"""WordSampler — weighted random sampling over any compatible scored-pair provider."""

import random

from nl_processing.core.models import ScoredWordPair, Word, WordPair

from nl_processing.sampling.ports import ScoredPairProvider


class WordSampler:
    """Weighted random sampling of practice items for language exercises."""

    def __init__(
        self,
        *,
        scored_store: ScoredPairProvider,
        exercise_type: str,
        positive_balance_weight: float = 0.01,
        negative_balance_weight: float = 100,
    ) -> None:
        self._progress_store = scored_store
        self._exercise_type = exercise_type

        self._positive_balance_weight = positive_balance_weight
        self._negative_balance_weight = negative_balance_weight

    async def sample(self) -> WordPair:
        """
        Return weighted-sampled word pair
        """
        scored = await self._progress_store.get_word_pairs_with_scores()
        if not scored:
            raise RuntimeError("No word pairs found in progress store")
        candidate_weights = [self._compute_weight(sp) for sp in scored]

        chosen = random.choices(scored, weights=candidate_weights, k=1)[0]
        return chosen.pair

    async def sample_adversarial(self, source_word: Word, limit: int) -> list[WordPair]:
        """Return uniform-random distractor pairs with same part of speech.

        Raises ValueError if source_word.language != source_language.
        Raises ValueError if limit <= 0.
        """
        if source_word.language != self._source_language:
            msg = (
                f"source_word language '{source_word.language.value}' does not match "
                f"sampler source_language '{self._source_language.value}'"
            )
            raise ValueError(msg)
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        scored = await self._progress_store.get_word_pairs_with_scores()
        candidates = [
            sp.pair
            for sp in scored
            if sp.pair.source.word_type == source_word.word_type
            and sp.pair.source.normalized_form != source_word.normalized_form
        ]
        if not candidates:
            return []
        if limit >= len(candidates):
            random.shuffle(candidates)
            return candidates
        return random.sample(candidates, limit)

    def _compute_weight(self, scored_pair: ScoredWordPair) -> float:
        """Compute sampling weight for a scored word pair."""
        score = scored_pair.scores.get(self._exercise_type, 0)
        if score > 0:
            return self._positive_balance_weight
        if score < 0:
            return self._negative_balance_weight
        return 1.0


class TieredMultiExerciseSampler:
    def __init__(
        self,
        *,
        scored_store: ScoredPairProvider,
        exercise_types: list[str],
        tiered_exercise_type: str,
        finished_exercise_weight: float = 0.01,
    ) -> None:
        self._progress_store = scored_store
        self._finished_exercise_weight = finished_exercise_weight
        self._exercise_types = exercise_types
        self._tiered_exercise_type = tiered_exercise_type

    async def sample(self) -> (str, WordPair):
        """
        :return: Exercise type and word pair
        """
        scored = await self._progress_store.get_word_pairs_with_scores()
        if not scored:
            raise RuntimeError("No word pairs found in progress store")
        candidate_weights = [self._compute_weight(sp) for sp in scored]

        chosen = random.choices(scored, weights=candidate_weights, k=1)[0]
        return chosen.pair

    def _choose_exercise_for_word(self, scored_pair: ScoredWordPair) -> str:
        is_repeat_mode = scored_pair.scores.get(self._tiered_exercise_type, 0) < 0
        if is_repeat_mode:
            # return the exercise name of the last positive score or first element if all scores negative
            for exercise_type in reversed(self._exercise_types):
                if scored_pair.scores.get(exercise_type, 0) > 0:
                    return exercise_type
            return self._exercise_types[0]

        # return the exercise name of the last non-positive score or last if all positive
        for exercise_type in reversed(self._exercise_types):
            if scored_pair.scores.get(exercise_type, 0) <= 0:
                return exercise_type
        return self._exercise_types[-1]

    def _compute_weight(self, scored_pair: ScoredWordPair) -> float:
        """Compute sampling weight for a scored word pair."""
        relevant_scores = [scored_pair.scores.get(exercise_type, 0) for exercise_type in self._exercise_types]
        min_score = min(relevant_scores)
        if min_score >= 0:
            return self._finished_exercise_weight
        return 1.0
