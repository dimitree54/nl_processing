"""ExerciseProgressStore — per-user, per-exercise score tracking.

Internal API consumed by the sampling module to determine which
words to practice based on exercise-specific scores.
"""

import os

from nl_processing.core.models import Language, PartOfSpeech, ScoredWordPair, Word, WordPair

from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.exceptions import ConfigurationError

_DATABASE_URL_MISSING = (
    "DATABASE_URL environment variable is required. "
    "Set it to your Neon PostgreSQL connection string. "
    "See: https://neon.tech/docs/connect/connect-from-any-app"
)


def _read_database_url() -> str:
    """Read DATABASE_URL from environment, raising ConfigurationError if absent."""
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        raise ConfigurationError(_DATABASE_URL_MISSING) from exc


class ExerciseProgressStore:
    """Per-user, per-exercise score tracking and score-aware word pair retrieval."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language,
        target_language: Language,
        exercise_types: list[str],
        backend: AbstractBackend | None = None,
    ) -> None:
        if not exercise_types:
            msg = "exercise_types must be a non-empty list"
            raise ValueError(msg)
        if backend is None:
            database_url = _read_database_url()
            self._backend: AbstractBackend = NeonBackend(database_url)
        else:
            self._backend = backend
        self._user_id = user_id
        self._source_language = source_language
        self._target_language = target_language
        src = source_language.value
        tgt = target_language.value
        self._exercise_types = list(exercise_types)
        self._score_tables: dict[str, str] = {et: f"{src}_{tgt}_{et}" for et in exercise_types}
        self._applied_events_table = f"applied_events_{src}_{tgt}"

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
        rows = await self._backend.get_user_words(
            self._user_id,
            self._source_language.value,
        )
        if not rows:
            return []
        source_word_ids = [int(row["source_id"]) for row in rows]
        scores_by_word: dict[int, dict[str, int]] = {}
        for et, table in self._score_tables.items():
            score_rows = await self._backend.get_user_exercise_scores(
                table,
                self._user_id,
                source_word_ids,
            )
            for score_row in score_rows:
                wid = int(score_row["source_word_id"])
                scores_by_word.setdefault(wid, {})[et] = int(score_row["score"])
        result: list[ScoredWordPair] = []
        for row in rows:
            pair = self._row_to_word_pair(row)
            wid = int(row["source_id"])
            word_scores = scores_by_word.get(wid, {})
            scores = {et: word_scores.get(et, 0) for et in self._exercise_types}
            result.append(
                ScoredWordPair(pair=pair, scores=scores, source_word_id=wid),
            )
        return result

    async def export_remote_snapshot(self) -> list[ScoredWordPair]:
        """Thin wrapper around get_word_pairs_with_scores for cache consumers."""
        return await self.get_word_pairs_with_scores()

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

    def _word_from_row(
        self,
        row: dict[str, str | int],
        prefix: str,
        lang: Language,
    ) -> Word:
        """Reconstruct a Word from a backend row using column prefix."""
        return Word(
            normalized_form=str(row[f"{prefix}_normalized_form"]),
            word_type=PartOfSpeech(row[f"{prefix}_word_type"]),
            language=lang,
        )

    def _row_to_word_pair(self, row: dict[str, str | int]) -> WordPair:
        """Reconstruct a WordPair from a backend row dict."""
        return WordPair(
            source=self._word_from_row(row, "source", self._source_language),
            target=self._word_from_row(row, "target", self._target_language),
        )
