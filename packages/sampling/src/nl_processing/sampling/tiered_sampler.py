"""TieredExerciseSampler — weighted random sampling over tiered candidates with exercise selection."""

import random

from nl_processing.core.models import Language
from nl_processing.core.tiered_models import TieredCandidate, TieredExerciseSelection
from nl_processing.core.tiered_ports import TieredCandidateProvider
from nl_processing.database.tiered_progress import TieredExerciseProgressStore


class TieredExerciseSampler:
    """Weighted random sampling of tiered exercise items for language practice."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language,
        target_language: Language,
        mode_slug: str,
        exercise_types: list[str],
        finished_word_weight: float = 0.01,
        tiered_store: TieredCandidateProvider | None = None,
    ) -> None:
        if not exercise_types:
            msg = "exercise_types must be a non-empty list"
            raise ValueError(msg)
        if not (0 < finished_word_weight <= 1):
            msg = f"finished_word_weight must be in (0, 1], got {finished_word_weight}"
            raise ValueError(msg)
        if not mode_slug:
            msg = "mode_slug must be non-empty"
            raise ValueError(msg)

        if tiered_store is not None:
            self._tiered_store: TieredCandidateProvider = tiered_store
        else:
            self._tiered_store = TieredExerciseProgressStore(
                user_id=user_id,
                source_language=source_language,
                target_language=target_language,
                mode_slug=mode_slug,
                exercise_types=exercise_types,
            )

        self._exercise_types = exercise_types
        self._finished_word_weight = finished_word_weight

    async def sample(self, limit: int) -> list[TieredExerciseSelection]:
        """Return weighted-sampled tiered exercise selections without replacement.

        Weight function:
        - If any participating exercise score is <= 0: weight = 1.0
        - If all participating exercise scores are > 0: weight = finished_word_weight

        If limit <= 0, return [].
        If limit >= candidates, return all in random order.
        """
        if limit <= 0:
            return []

        candidates = await self._tiered_store.get_tiered_candidates()
        if not candidates:
            return []

        weights = [self._compute_weight(candidate) for candidate in candidates]

        if limit >= len(candidates):
            selections = [
                TieredExerciseSelection(
                    pair=candidate.pair,
                    source_word_id=candidate.source_word_id,
                    exercise_type=self._select_exercise(candidate),
                    in_repeat_mode=candidate.in_repeat_mode,
                )
                for candidate in candidates
            ]
            random.shuffle(selections)
            return selections

        candidate_list = list(candidates)
        candidate_weights = list(weights)
        selected: list[TieredExerciseSelection] = []

        for _i in range(limit):
            chosen = random.choices(candidate_list, weights=candidate_weights, k=1)[0]
            idx = candidate_list.index(chosen)

            selection = TieredExerciseSelection(
                pair=chosen.pair,
                source_word_id=chosen.source_word_id,
                exercise_type=self._select_exercise(chosen),
                in_repeat_mode=chosen.in_repeat_mode,
            )
            selected.append(selection)

            candidate_list.pop(idx)
            candidate_weights.pop(idx)

        return selected

    def _compute_weight(self, candidate: TieredCandidate) -> float:
        """Compute sampling weight for a tiered candidate."""
        if not candidate.scores:
            return 1.0

        # Check if any participating exercise score is <= 0
        for exercise_type in self._exercise_types:
            if exercise_type in candidate.scores and candidate.scores[exercise_type] <= 0:
                return 1.0

        # All participating exercise scores are > 0
        return self._finished_word_weight

    def _select_exercise(self, candidate: TieredCandidate) -> str:
        """Select the appropriate exercise for a tiered candidate."""
        if candidate.in_repeat_mode:
            # Repeat mode: choose the most complex (last in ordered list) exercise whose score is > 0
            positive_exercises = []
            for exercise_type in self._exercise_types:
                if exercise_type in candidate.scores and candidate.scores[exercise_type] > 0:
                    positive_exercises.append(exercise_type)

            if not positive_exercises:
                msg = "Invalid repeat state: in repeat mode but no positive scores"
                raise ValueError(msg)

            # Return the most complex (last in exercise_types order) among positive exercises
            for exercise_type in reversed(self._exercise_types):
                if exercise_type in positive_exercises:
                    return exercise_type

            # This should never be reached due to the check above
            msg = "Invalid repeat state: in repeat mode but no positive scores"  # pragma: no cover
            raise ValueError(msg)  # pragma: no cover

        else:
            # Normal mode: choose the most complex (last in ordered list) exercise whose score is <= 0
            non_positive_exercises = []
            for exercise_type in self._exercise_types:
                score = candidate.scores.get(exercise_type, 0)
                if score <= 0:
                    non_positive_exercises.append(exercise_type)

            if non_positive_exercises:
                # Return the most complex (last in exercise_types order) among non-positive exercises
                for exercise_type in reversed(self._exercise_types):
                    if exercise_type in non_positive_exercises:
                        return exercise_type

            # Fully finished review case: all scores > 0, not in repeat
            # Show the most complex exercise (last in list)
            return self._exercise_types[-1]
