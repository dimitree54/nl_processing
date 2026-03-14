"""TieredExerciseProgressStore — tiered exercise progress with repeat-state management.

Implements TieredCandidateProvider and RemoteTieredSyncPort protocols for
tiered exercise flows.
"""

from nl_processing.core.models import Language
from nl_processing.core.tiered_models import (
    TieredCandidate,
    TieredProgressSummary,
    TieredSnapshotEntry,
)

from nl_processing.database._database_config import read_database_url
from nl_processing.database._tiered_backend_ops import (
    build_tiered_candidates,
    build_tiered_snapshot_entries,
    get_current_repeat_state,
    get_repeat_states_for_user_mode,
    get_rows_with_scores,
    read_scores_after_update,
    update_repeat_state,
)
from nl_processing.database._tiered_helpers import (
    compute_next_repeat_state,
    compute_tiered_progress,
)
from nl_processing.database.backend._neon_tiered import create_tiered_tables
from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.exceptions import DatabaseError


class TieredExerciseProgressStore:
    """Per-user progress store for tiered exercise flows with repeat-state management."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language,
        target_language: Language,
        mode_slug: str,
        exercise_types: list[str],
        backend: AbstractBackend | None = None,
    ) -> None:
        if not mode_slug.strip():
            msg = "mode_slug must be a non-empty string"
            raise ValueError(msg)
        if not exercise_types:
            msg = "exercise_types must be a non-empty list"
            raise ValueError(msg)

        if backend is None:
            database_url = read_database_url()
            self._backend: AbstractBackend = NeonBackend(database_url)
        else:
            self._backend = backend

        self._user_id = user_id
        self._source_language = source_language
        self._target_language = target_language
        self._mode_slug = mode_slug
        self._exercise_types = list(exercise_types)

        src = source_language.value
        tgt = target_language.value
        self._src = src
        self._tgt = tgt
        self._score_tables: dict[str, str] = {et: f"{src}_{tgt}_{et}" for et in exercise_types}
        self._applied_events_table = f"applied_events_{src}_{tgt}"

    async def get_tiered_candidates(self) -> list[TieredCandidate]:
        """Return all translated word pairs for the user with exercise scores and repeat-state."""
        rows, scores_by_word = await get_rows_with_scores(
            self._backend, self._user_id, self._source_language, self._score_tables
        )
        if not rows:
            return []

        # Get repeat-state data
        repeat_states = await self._get_repeat_states()
        repeat_state_by_word = {int(rs["source_word_id"]): True for rs in repeat_states}

        return build_tiered_candidates(
            rows,
            scores_by_word,
            repeat_state_by_word,
            self._exercise_types,
            self._source_language,
            self._target_language,
        )

    async def get_tiered_progress_summary(self) -> TieredProgressSummary:
        """Return tiered progress summary using all-positive completion rule."""
        candidates = await self.get_tiered_candidates()
        return compute_tiered_progress(candidates, self._exercise_types)

    async def apply_tiered_result(self, *, event_id: str, source_word_id: int, exercise_type: str, delta: int) -> None:
        """Apply tiered result atomically: score delta + repeat-state update."""
        self._validate_exercise_type(exercise_type)
        if delta not in (1, -1):
            msg = f"delta must be +1 or -1, got {delta}"
            raise ValueError(msg)

        # Use the existing atomic apply pattern
        applied = await self._backend.apply_score_delta_atomic(
            score_table=self._score_tables[exercise_type],
            events_table=self._applied_events_table,
            user_id=self._user_id,
            event_id=event_id,
            source_word_id=source_word_id,
            delta=delta,
        )

        if not applied:
            return  # Event was already applied

        # Now handle repeat-state update
        if not isinstance(self._backend, NeonBackend):
            msg = "Tiered functionality requires NeonBackend"
            raise DatabaseError(msg)

        try:
            # Read all participating scores for this word after update
            scores_after_update = await read_scores_after_update(
                self._backend, self._exercise_types, self._score_tables, self._user_id, source_word_id
            )

            # Get current repeat state
            current_in_repeat = await get_current_repeat_state(
                self._backend, self._src, self._tgt, self._user_id, self._mode_slug, source_word_id
            )

            # Compute next repeat state
            next_in_repeat = compute_next_repeat_state(
                current_in_repeat, delta, scores_after_update, self._exercise_types
            )

            # Update repeat state if needed
            await update_repeat_state(
                self._backend,
                self._src,
                self._tgt,
                self._user_id,
                self._mode_slug,
                source_word_id,
                next_in_repeat,
                current_in_repeat,
            )

        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    async def export_tiered_snapshot(self) -> list[TieredSnapshotEntry]:
        """Return all candidates as TieredSnapshotEntry with target_word_id included."""
        rows, scores_by_word = await get_rows_with_scores(
            self._backend, self._user_id, self._source_language, self._score_tables
        )
        if not rows:
            return []

        # Get repeat-state data
        repeat_states = await self._get_repeat_states()
        repeat_state_by_word = {int(rs["source_word_id"]): True for rs in repeat_states}

        return build_tiered_snapshot_entries(
            rows,
            scores_by_word,
            repeat_state_by_word,
            self._exercise_types,
            self._source_language,
            self._target_language,
        )

    def _validate_exercise_type(self, exercise_type: str) -> None:
        """Raise ValueError if exercise_type is not in the configured set."""
        if exercise_type not in self._score_tables:
            msg = f"Unknown exercise_type '{exercise_type}'; expected one of {sorted(self._score_tables)}"
            raise ValueError(msg)

    async def _get_repeat_states(self) -> list[dict[str, str | int]]:
        """Fetch repeat-state rows for the current user and mode."""
        if not isinstance(self._backend, NeonBackend):
            msg = "Tiered functionality requires NeonBackend"
            raise DatabaseError(msg)
        return await get_repeat_states_for_user_mode(
            self._backend, self._src, self._tgt, self._user_id, self._mode_slug
        )

    async def _ensure_tiered_tables_exist(self) -> None:
        """Ensure tiered repeat-state tables exist."""
        if not isinstance(self._backend, NeonBackend):
            msg = "Tiered functionality requires NeonBackend"
            raise DatabaseError(msg)

        conn = await self._backend._connect()  # noqa: SLF001
        await create_tiered_tables(conn, [(self._src, self._tgt)])
