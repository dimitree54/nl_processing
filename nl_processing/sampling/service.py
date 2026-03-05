"""WordSampler — weighted random sampling of practice items for language exercises."""

import random

from nl_processing.core.models import Language, Word
from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database.models import ScoredWordPair, WordPair


class WordSampler:
    """Weighted random sampling of practice items for language exercises."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
        exercise_types: list[str],
        positive_balance_weight: float = 0.01,
    ) -> None:
        if not exercise_types:
            msg = "exercise_types must be a non-empty list"
            raise ValueError(msg)
        if not (0 < positive_balance_weight <= 1):
            msg = f"positive_balance_weight must be in (0, 1], got {positive_balance_weight}"
            raise ValueError(msg)
        self._progress_store = ExerciseProgressStore(
            user_id=user_id,
            source_language=source_language,
            target_language=target_language,
        )
        self._exercise_types = exercise_types
        self._positive_balance_weight = positive_balance_weight
        self._source_language = source_language

    async def sample(self, limit: int) -> list[WordPair]:
        """Return weighted-sampled word pairs without replacement.

        Weight function (v1):
        - min_score = min(scores[et] for et in exercise_types)
        - If min_score > 0: weight = positive_balance_weight
        - If min_score <= 0: weight = 1.0

        If limit <= 0, return [].
        If limit >= candidates, return all in random order.
        """
        if limit <= 0:
            return []
        scored = await self._progress_store.get_word_pairs_with_scores(self._exercise_types)
        if not scored:
            return []
        weights = [self._compute_weight(sp) for sp in scored]
        if limit >= len(scored):
            pairs = [sp.pair for sp in scored]
            random.shuffle(pairs)
            return pairs
        candidates = list(scored)
        candidate_weights = list(weights)
        selected: list[WordPair] = []
        for _i in range(limit):
            chosen = random.choices(candidates, weights=candidate_weights, k=1)[0]
            idx = candidates.index(chosen)
            selected.append(chosen.pair)
            candidates.pop(idx)
            candidate_weights.pop(idx)
        return selected

    async def sample_adversarial(self, source_word: Word, limit: int) -> list[WordPair]:
        """Return uniform-random distractor pairs with same part of speech.

        Raises ValueError if source_word.language != source_language.
        Returns [] if limit <= 0.
        """
        if source_word.language != self._source_language:
            msg = (
                f"source_word language '{source_word.language.value}' does not match "
                f"sampler source_language '{self._source_language.value}'"
            )
            raise ValueError(msg)
        if limit <= 0:
            return []
        scored = await self._progress_store.get_word_pairs_with_scores([])
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
        if not scored_pair.scores:
            return 1.0
        min_score = min(scored_pair.scores[et] for et in self._exercise_types)
        if min_score > 0:
            return self._positive_balance_weight
        return 1.0
