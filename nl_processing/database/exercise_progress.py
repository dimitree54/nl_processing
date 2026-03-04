"""ExerciseProgressStore — per-user, per-exercise score tracking.

Internal API consumed by the sampling module to determine which
words to practice based on exercise-specific scores.
"""

import os

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.exceptions import ConfigurationError, DatabaseError
from nl_processing.database.logging import get_logger
from nl_processing.database.models import ScoredWordPair, WordPair

_logger = get_logger("exercise_progress")

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
    ) -> None:
        database_url = _read_database_url()
        self._backend = NeonBackend(database_url)
        self._user_id = user_id
        self._source_language = source_language
        self._target_language = target_language
        src = source_language.value
        tgt = target_language.value
        self._source_table = f"words_{src}"
        self._score_table = f"{src}_{tgt}"

    async def increment(
        self,
        source_word: Word,
        exercise_type: str,
        delta: int,
    ) -> None:
        """Update the score for a word+exercise by delta (+1 or -1).

        Raises ValueError if delta is not +1 or -1.
        Raises DatabaseError if the source word is not found.
        """
        if delta not in (1, -1):
            msg = f"delta must be +1 or -1, got {delta}"
            raise ValueError(msg)
        row = await self._backend.get_word(
            self._source_language.value,
            source_word.normalized_form,
        )
        if row is None:
            msg = f"Cannot increment score: word '{source_word.normalized_form}' not found in {self._source_table}"
            raise DatabaseError(msg)
        word_id = int(row["id"])
        await self._backend.increment_user_exercise_score(
            self._score_table,
            self._user_id,
            word_id,
            exercise_type,
            delta,
        )

    async def get_word_pairs_with_scores(
        self,
        exercise_types: list[str],
    ) -> list[ScoredWordPair]:
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
        score_rows = await self._backend.get_user_exercise_scores(
            self._score_table,
            self._user_id,
            source_word_ids,
            exercise_types,
        )
        scores_by_word: dict[int, dict[str, int]] = {}
        for score_row in score_rows:
            wid = int(score_row["source_word_id"])
            etype = str(score_row["exercise_type"])
            scores_by_word.setdefault(wid, {})[etype] = int(score_row["score"])
        result: list[ScoredWordPair] = []
        for row in rows:
            pair = self._row_to_word_pair(row)
            wid = int(row["source_id"])
            word_scores = scores_by_word.get(wid, {})
            scores = {et: word_scores.get(et, 0) for et in exercise_types}
            result.append(ScoredWordPair(pair=pair, scores=scores))
        return result

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
