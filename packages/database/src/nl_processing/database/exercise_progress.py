"""ExerciseProgressStore — per-user, per-exercise score tracking.

Default implementation of the shared scored-pair and remote-progress
sync contracts used by sampling and database_cache.
"""

from datetime import datetime

from nl_processing.core.models import Language, ScoredWordPair, WordPairSnapshot
from nl_processing.database_core._database_config import read_database_url
from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.backend.neon import NeonBackend

from nl_processing.database._row_helpers import row_to_word_pair


def _build_progress_backend(
    exercise_types: list[str],
    source_language: Language,
    target_language: Language,
    backend: AbstractBackend | None,
) -> tuple[AbstractBackend, dict[str, str], str]:
    """Build backend and remote table names for the progress store."""
    if not exercise_types:
        msg = "exercise_types must be a non-empty list"
        raise ValueError(msg)
    active_backend = backend or NeonBackend(read_database_url())
    src = source_language.value
    tgt = target_language.value
    score_tables = {exercise_type: f"{src}_{tgt}_{exercise_type}" for exercise_type in exercise_types}
    applied_events_table = f"applied_events_{src}_{tgt}"
    return active_backend, score_tables, applied_events_table


class ExerciseProgressStore:
    """Per-user progress store for score-aware reads and remote cache sync."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language,
        target_language: Language,
        exercise_types: list[str],
        backend: AbstractBackend | None = None,
    ) -> None:
        self._backend, self._score_tables, self._applied_events_table = _build_progress_backend(
            exercise_types, source_language, target_language, backend
        )
        self._user_id = user_id
        self._source_language = source_language
        self._target_language = target_language
        self._exercise_types = list(exercise_types)

    async def increment(
        self,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None:
        """Update the score for a word+exercise by delta (+1 or -1).

        Raises ValueError if delta is not +1 or -1, or exercise_type is unknown.
        """
        if delta not in (1, -1):
            msg = f"delta must be +1 or -1, got {delta}"
            raise ValueError(msg)
        self._validate_exercise_type(exercise_type)
        table = self._score_tables[exercise_type]
        await self._backend.increment_user_exercise_score(
            table,
            self._user_id,
            source_word_id,
            delta,
        )

    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]:
        """Return all translated word pairs for the user with exercise scores.

        Missing scores default to 0 (FR33).
        """
        rows, scores_by_word = await self._get_rows_with_scores()
        if not rows:
            return []
        result: list[ScoredWordPair] = []
        for row in rows:
            pair = row_to_word_pair(row, self._source_language, self._target_language)
            source_word_id = int(row["source_id"])  # type: ignore[arg-type]
            word_scores = scores_by_word.get(source_word_id, {})
            scores = {et: word_scores.get(et, 0) for et in self._exercise_types}
            result.append(
                ScoredWordPair(
                    pair=pair,
                    scores=scores,
                ),
            )
        return result

    async def export_remote_snapshot(self) -> list[WordPairSnapshot]:
        """Return score-aware pairs with stable remote IDs for cache consumers."""
        rows, scores_by_word = await self._get_rows_with_scores()
        if not rows:
            return []
        snapshots: list[WordPairSnapshot] = []
        for row in rows:
            pair = row_to_word_pair(row, self._source_language, self._target_language)
            source_word_id = int(row["source_id"])  # type: ignore[arg-type]
            target_word_id = int(row["target_id"])  # type: ignore[arg-type]
            added_at = row["added_at"]  # type: ignore[assignment]  # datetime from T1
            word_scores = scores_by_word.get(source_word_id, {})
            scores = {et: word_scores.get(et, 0) for et in self._exercise_types}
            snapshots.append(
                WordPairSnapshot(
                    pair=pair,
                    scores=scores,
                    source_word_id=source_word_id,
                    target_word_id=target_word_id,
                    added_at=added_at,
                ),
            )
        return snapshots

    async def apply_score_delta(
        self,
        event_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None:
        """Apply a score delta idempotently, guarded by event deduplication.

        Validates exercise_type and delta. Skips if event_id was already applied.
        The check-increment-mark operation is atomic (single transaction).
        """
        self._validate_exercise_type(exercise_type)
        if delta not in (1, -1):
            msg = f"delta must be +1 or -1, got {delta}"
            raise ValueError(msg)
        table = self._score_tables[exercise_type]
        await self._backend.apply_score_delta_atomic(
            score_table=table,
            events_table=self._applied_events_table,
            user_id=self._user_id,
            event_id=event_id,
            source_word_id=source_word_id,
            delta=delta,
        )

    def _validate_exercise_type(self, exercise_type: str) -> None:
        """Raise ValueError if exercise_type is not in the configured set."""
        if exercise_type not in self._score_tables:
            msg = f"Unknown exercise_type '{exercise_type}'; expected one of {sorted(self._score_tables)}"
            raise ValueError(msg)

    async def _get_rows_with_scores(
        self,
    ) -> tuple[list[dict[str, str | int | datetime]], dict[int, dict[str, int]]]:
        """Fetch translated rows and per-exercise scores for the current user."""
        rows = await self._backend.get_user_words(
            self._user_id,
            self._source_language.value,
        )
        if not rows:
            return [], {}
        source_word_ids = [int(row["source_id"]) for row in rows]  # type: ignore[arg-type]
        scores_by_word: dict[int, dict[str, int]] = {}
        for exercise_type, table in self._score_tables.items():
            score_rows = await self._backend.get_user_exercise_scores(
                table,
                self._user_id,
                source_word_ids,
            )
            for score_row in score_rows:
                wid = int(score_row["source_word_id"])
                scores_by_word.setdefault(wid, {})[exercise_type] = int(score_row["score"])
        return rows, scores_by_word
