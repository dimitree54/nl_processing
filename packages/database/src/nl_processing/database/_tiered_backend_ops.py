"""Backend operations helper for tiered exercise progress."""

from nl_processing.core.models import Language
from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.backend.neon import NeonBackend
from nl_processing.database_core.exceptions import DatabaseError

from nl_processing.database._row_helpers import row_to_word_pair
from nl_processing.database._tiered_helpers import validate_repeat_state_integrity
from nl_processing.database.backend._neon_tiered import (
    delete_repeat_state_impl,
    get_repeat_states_impl,
    upsert_repeat_state_impl,
)
from nl_processing.database.backend._queries import get_scores_query
from nl_processing.database.backend._tiered_queries import get_repeat_state
from nl_processing.database.tiered_models import TieredCandidate, TieredSnapshotEntry


async def read_scores_after_update(
    backend: NeonBackend,
    exercise_types: list[str],
    score_tables: dict[str, str],
    user_id: str,
    source_word_id: int,
) -> dict[str, int]:
    """Read all participating scores for a word after an update."""
    conn = await backend._connect()  # noqa: SLF001
    scores_after_update = {}

    for et in exercise_types:
        et_table = score_tables[et]
        score_row = await conn.fetchrow(
            get_scores_query(et_table).replace(
                "WHERE user_id = $1\n        AND source_word_id = ANY($2)", "WHERE user_id = $1 AND source_word_id = $2"
            ),
            user_id,
            source_word_id,
        )
        scores_after_update[et] = int(score_row["score"]) if score_row else 0

    return scores_after_update


async def get_current_repeat_state(
    backend: NeonBackend,
    src: str,
    tgt: str,
    user_id: str,
    mode_slug: str,
    source_word_id: int,
) -> bool:
    """Get current repeat state for a word."""
    conn = await backend._connect()  # noqa: SLF001
    current_repeat_row = await conn.fetchrow(
        get_repeat_state(src, tgt),
        user_id,
        mode_slug,
        source_word_id,
    )
    return current_repeat_row is not None


async def update_repeat_state(
    backend: NeonBackend,
    src: str,
    tgt: str,
    user_id: str,
    mode_slug: str,
    source_word_id: int,
    next_in_repeat: bool,
    current_in_repeat: bool,
) -> None:
    """Update repeat state if needed."""
    if next_in_repeat != current_in_repeat:
        conn = await backend._connect()  # noqa: SLF001
        if next_in_repeat:
            # Activate repeat state
            await upsert_repeat_state_impl(conn, src, tgt, user_id, mode_slug, source_word_id)
        else:
            # Deactivate repeat state
            await delete_repeat_state_impl(conn, src, tgt, user_id, mode_slug, source_word_id)


async def get_repeat_states_for_user_mode(
    backend: NeonBackend,
    src: str,
    tgt: str,
    user_id: str,
    mode_slug: str,
) -> list[dict[str, str | int]]:
    """Fetch repeat-state rows for the current user and mode."""
    if not isinstance(backend, NeonBackend):
        msg = "Tiered functionality requires NeonBackend"
        raise DatabaseError(msg)

    conn = await backend._connect()  # noqa: SLF001
    return await get_repeat_states_impl(conn, src, tgt, user_id, mode_slug)


def build_tiered_candidates(
    rows: list[dict],
    scores_by_word: dict[int, dict[str, int]],
    repeat_state_by_word: dict[int, bool],
    exercise_types: list[str],
    source_language: Language,
    target_language: Language,
) -> list[TieredCandidate]:
    """Build tiered candidates from database rows and scores."""
    result: list[TieredCandidate] = []
    for row in rows:
        pair = row_to_word_pair(row, source_language, target_language)
        wid = int(row["source_id"])  # type: ignore[arg-type]
        word_scores = scores_by_word.get(wid, {})
        scores = {et: word_scores.get(et, 0) for et in exercise_types}
        in_repeat = repeat_state_by_word.get(wid, False)

        # Validate repeat-state integrity per TBR-DB-6
        validate_repeat_state_integrity(in_repeat, scores, exercise_types)

        result.append(
            TieredCandidate(
                pair=pair,
                source_word_id=wid,
                scores=scores,
                in_repeat_mode=in_repeat,
            ),
        )
    return result


def build_tiered_snapshot_entries(
    rows: list[dict],
    scores_by_word: dict[int, dict[str, int]],
    repeat_state_by_word: dict[int, bool],
    exercise_types: list[str],
    source_language: Language,
    target_language: Language,
) -> list[TieredSnapshotEntry]:
    """Build snapshot entries from database rows and scores."""
    snapshots: list[TieredSnapshotEntry] = []
    for row in rows:
        pair = row_to_word_pair(row, source_language, target_language)
        source_word_id = int(row["source_id"])  # type: ignore[arg-type]
        target_word_id = int(row["target_id"])  # type: ignore[arg-type]
        word_scores = scores_by_word.get(source_word_id, {})
        scores = {et: word_scores.get(et, 0) for et in exercise_types}
        in_repeat = repeat_state_by_word.get(source_word_id, False)

        snapshots.append(
            TieredSnapshotEntry(
                source_word_id=source_word_id,
                target_word_id=target_word_id,
                pair=pair,
                scores=scores,
                in_repeat_mode=in_repeat,
            ),
        )
    return snapshots


async def get_rows_with_scores(
    backend: AbstractBackend,
    user_id: str,
    source_language: Language,
    score_tables: dict[str, str],
) -> tuple[list[dict], dict[int, dict[str, int]]]:
    """Fetch translated rows and per-exercise scores for the current user."""
    rows = await backend.get_user_words(user_id, source_language.value)
    if not rows:
        return [], {}
    source_word_ids = [int(row["source_id"]) for row in rows]  # type: ignore[arg-type]
    scores_by_word: dict[int, dict[str, int]] = {}
    for exercise_type, table in score_tables.items():
        score_rows = await backend.get_user_exercise_scores(table, user_id, source_word_ids)
        for score_row in score_rows:
            wid = int(score_row["source_word_id"])
            scores_by_word.setdefault(wid, {})[exercise_type] = int(score_row["score"])
    return rows, scores_by_word
