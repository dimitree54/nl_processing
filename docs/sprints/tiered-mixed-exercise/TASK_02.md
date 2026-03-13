---
Task ID: T2
Title: Implement `TieredExerciseProgressStore` in `database`
Sprint: `2026-03-14_tiered-mixed-exercise`
Module: database
Depends on: T1
Parallelizable: yes, with T4
---

## Goal / value

After this task, the `database` package exposes a fully tested `TieredExerciseProgressStore` that manages a dedicated remote `user_word_tiered_repeat_state_<src>_<tgt>` table, provides tiered candidate reads with ordered scores and repeat-state, computes mixed progress summaries (all-scores-positive rule), performs atomic tiered answer replay (score + repeat-state transition), and exports tiered snapshots for cache rebuilds. All existing `ExerciseProgressStore` behavior remains untouched.

## Context (contract mapping)

- Spec: `packages/database/docs/module-spec.md` Section 5 (TFR-DB-1..8, TBR-DB-1..6, TIF-DB-1..4, TDEC-DB-1..4, TAC-DB-1..4)
- Core tiered models from T1: `TieredCandidate`, `TieredProgressSummary`, `TieredSnapshotEntry`
- Core tiered ports from T1: `TieredCandidateProvider`, `RemoteTieredSyncPort`
- Existing patterns: `exercise_progress.py`, `backend/abstract.py`, `backend/_neon_exercise.py`, `backend/_queries.py`

## Preconditions

- T1 completed: `core` has `TieredCandidate`, `TieredProgressSummary`, `TieredSnapshotEntry`, `TieredCandidateProvider`, `RemoteTieredSyncPort`.
- `make -C packages/database check` passes before starting.

## Non-goals

- Modifying `ExerciseProgressStore`, `DatabaseService`, or `DetailedWordStore`.
- Modifying existing score tables or `applied_events` tables.
- Implementing cache-side logic (that's T3).
- Implementing sampling logic (that's T4).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**

- `packages/database/src/nl_processing/database/` -- add tiered store, tiered backend operations, tiered queries, tiered models
- `packages/database/tests/` -- add tiered tests

**FORBIDDEN -- this task must NEVER touch:**

- `packages/core/` (already done in T1)
- `packages/database_cache/`, `packages/sampling/`
- Existing `exercise_progress.py`, `service.py`, `models.py`, `backend/abstract.py`, `backend/neon.py` -- do NOT modify these
- `docs/`, `Makefile`, `pyproject.toml`, `ruff.toml`

**Test scope:**

- Tests go in: `packages/database/tests/unit/database/` and `packages/database/tests/integration/database/`
- Test command: `make -C packages/database check`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- NEW: `packages/database/src/nl_processing/database/tiered_progress.py` -- `TieredExerciseProgressStore` class
- NEW: `packages/database/src/nl_processing/database/_tiered_helpers.py` -- repeat-state transition logic, tiered progress computation
- NEW: `packages/database/src/nl_processing/database/backend/_tiered_queries.py` -- SQL for repeat-state table DDL and CRUD
- NEW: `packages/database/src/nl_processing/database/backend/_neon_tiered.py` -- asyncpg operations for repeat-state table
- NEW: `packages/database/tests/unit/database/test_tiered_transition.py` -- unit tests for repeat-state transition matrix
- NEW: `packages/database/tests/unit/database/test_tiered_progress_summary.py` -- unit tests for all-positive progress math
- NEW: `packages/database/tests/integration/database/test_tiered_store.py` -- integration tests against real Neon PostgreSQL

## Dependencies and sequencing notes

- Depends on T1 for shared DTOs (`TieredCandidate`, `TieredProgressSummary`, `TieredSnapshotEntry`, `RemoteTieredSyncPort`).
- Can run in parallel with T4 (sampling), which only depends on T1's protocol definition.
- T3 (cache) depends on this task for remote sync contract implementation.

## Third-party / library research (mandatory for any external dependency)

No new third-party dependencies. Uses existing:

- **asyncpg** (already used throughout `backend/` for PostgreSQL operations)
- **pydantic** (already used for models)

## Implementation steps (developer-facing)

1. **Create `packages/database/src/nl_processing/database/backend/_tiered_queries.py`** with SQL for:
   - `create_tiered_repeat_state_table(src, tgt)` -- DDL for `user_word_tiered_repeat_state_<src>_<tgt>` with columns: `user_id VARCHAR NOT NULL`, `mode_slug VARCHAR NOT NULL`, `source_word_id INTEGER NOT NULL`, `activated_at TIMESTAMP NOT NULL DEFAULT NOW()`, with `UNIQUE(user_id, mode_slug, source_word_id)`.
   - `upsert_repeat_state(src, tgt)` -- INSERT ON CONFLICT DO NOTHING (idempotent activation).
   - `delete_repeat_state(src, tgt)` -- DELETE one row by `(user_id, mode_slug, source_word_id)`.
   - `get_repeat_states(src, tgt)` -- SELECT all repeat-state rows for a user and mode_slug.
   - `get_repeat_state(src, tgt)` -- SELECT one repeat-state row for a `(user_id, mode_slug, source_word_id)`.

2. **Create `packages/database/src/nl_processing/database/backend/_neon_tiered.py`** with async functions wrapping the queries above. Follow the same pattern as `_neon_exercise.py`: accept `asyncpg.Connection`, delegate to query builders, wrap `asyncpg.PostgresError` as `DatabaseError`.

3. **Extend `backend/abstract.py`** with abstract methods for tiered operations: `create_tiered_tables`, `upsert_repeat_state`, `delete_repeat_state`, `get_repeat_states`, `get_repeat_state`. Add these at the end of the class, keeping the file under 200 lines. If the file would exceed 200 lines, extract a `_tiered_abstract.py` mixin.

4. **Extend `backend/neon.py`** with concrete implementations delegating to `_neon_tiered.py`. Keep the file under 200 lines -- if needed, the new tiered methods can go in a dedicated `_neon_tiered.py` module and be called from `neon.py`.

5. **Create `packages/database/src/nl_processing/database/_tiered_helpers.py`** with:
   - `compute_next_repeat_state(current_in_repeat: bool, delta: int, scores_after_update: dict[str, int], exercise_types: list[str]) -> bool` -- Pure function implementing TBR-DB-3..6:
     - Wrong answer (delta=-1) + not in repeat + has at least one positive score after update -> activate repeat mode.
     - Wrong answer (delta=-1) + not in repeat + no positive score after update -> do NOT activate repeat mode (nothing to repeat).
     - Correct answer (delta=+1) + in repeat -> deactivate repeat mode.
     - Wrong answer (delta=-1) + already in repeat + still has at least one positive score -> keep repeat mode.
     - Wrong answer (delta=-1) + already in repeat + no positive score left -> deactivate repeat mode.
   - `validate_repeat_state_integrity(in_repeat: bool, scores: dict[str, int], exercise_types: list[str]) -> None` -- Raises `ValueError` per TBR-DB-6 if `in_repeat=True` but no participating score is positive.
   - `compute_tiered_progress(candidates: list[TieredCandidate], exercise_types: list[str]) -> TieredProgressSummary` -- Counts a word as fully completed only when all participating exercise scores are `> 0` (TFR-DB-5). Missing scores default to `0` (TBR-DB-2).

6. **Create `packages/database/src/nl_processing/database/tiered_progress.py`** with `TieredExerciseProgressStore`:
   - Constructor: `__init__(self, *, user_id, source_language, target_language, mode_slug, exercise_types, backend=None)`. Validates `mode_slug` is non-empty, validates `exercise_types` is non-empty, stores ordered exercises (TBR-DB-1). Creates backend if not injected.
   - `async def get_tiered_candidates(self) -> list[TieredCandidate]`: Reuse existing `_get_rows_with_scores()` pattern from `ExerciseProgressStore` -- fetch user words, fetch per-exercise scores, fetch repeat-state rows for the mode_slug, join into `TieredCandidate` list. Validate repeat-state integrity (TBR-DB-6).
   - `async def get_tiered_progress_summary(self) -> TieredProgressSummary`: Call `get_tiered_candidates()` then `compute_tiered_progress()`.
   - `async def apply_tiered_result(self, *, event_id, source_word_id, exercise_type, delta) -> None`: In one transaction: apply the score delta via `apply_score_delta_atomic`, read all participating scores for this word, compute next repeat-state, update repeat-state table accordingly. Must be idempotent via event dedup.
   - `async def export_tiered_snapshot(self) -> list[TieredSnapshotEntry]`: Return all candidates as `TieredSnapshotEntry` with `target_word_id` included.

7. **Create unit tests:**
   - `test_tiered_transition.py`: Test `compute_next_repeat_state` against the full transition matrix:
     - wrong answer, not in repeat, has positive -> activate
     - wrong answer, not in repeat, no positive -> don't activate
     - correct answer, in repeat -> deactivate
     - wrong answer, in repeat, has positive -> keep
     - wrong answer, in repeat, no positive -> deactivate
     - correct answer, not in repeat -> stay not in repeat
   - Test `validate_repeat_state_integrity` raises on invalid state.
   - `test_tiered_progress_summary.py`: Test `compute_tiered_progress` with various score distributions.

8. **Create integration tests:**
   - `test_tiered_store.py`: Test against real Neon PostgreSQL:
     - Table creation for repeat-state table.
     - Full lifecycle: add words, get tiered candidates (all zero scores, not in repeat), apply a wrong answer (score goes negative, check repeat-state activation), apply a correct answer (check repeat-state deactivation), verify progress summary.
     - Idempotent replay (same event_id applied twice, no double-counting).
     - Snapshot export returns consistent data.

9. **Run `make -C packages/database check`** and verify all tests (existing + new) pass.

## Production safety constraints (mandatory)

- **Database operations**: All reads/writes must target the **testing/development database only** via Doppler-managed `DATABASE_URL`.
- The new `user_word_tiered_repeat_state_<src>_<tgt>` table uses `CREATE TABLE IF NOT EXISTS` -- safe for idempotent creation.
- Integration tests must use UUID-based user IDs for data isolation, matching the pattern in existing `conftest.py`.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuse `ExerciseProgressStore`'s score-reading pattern and `AbstractBackend`'s existing methods for score operations. The tiered store only adds repeat-state management on top.
- **Correct libraries only**: `asyncpg` (already in lockfile/pyproject).
- **Correct file locations**: New files follow the existing `backend/_neon_*.py`, `backend/_queries*.py`, `_*_helpers.py` naming patterns.
- **No regressions**: Existing `ExerciseProgressStore` tests and all current database tests must pass unchanged.

## Error handling + correctness rules (mandatory)

- Wrap all `asyncpg.PostgresError` as `DatabaseError` (existing pattern).
- `validate_repeat_state_integrity` must raise `ValueError` for invalid states per TBR-DB-6 -- never silently normalize.
- Unknown `exercise_type` in `apply_tiered_result` must raise `ValueError`.
- `delta` not in `(1, -1)` must raise `ValueError`.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove. This is a purely additive task.
- Do not create placeholder methods "for later."

## Acceptance criteria (testable)

1. `TieredExerciseProgressStore` can be constructed with valid params and raises `ValueError` for empty `mode_slug` or empty `exercise_types`.
2. `get_tiered_candidates()` returns `TieredCandidate` list with correct scores and repeat-state for all translated user words in the configured mode (TAC-DB-2).
3. `get_tiered_progress_summary()` counts a word as fully completed only when all participating exercise scores are `> 0` (TAC-DB-4).
4. `apply_tiered_result()` updates score and repeat-state atomically and idempotently (TAC-DB-3).
5. Repeat-state transitions match the full transition matrix (TBR-DB-3..6).
6. Invalid repeat-state (in_repeat=True with no positive score) raises an explicit error (TBR-DB-6).
7. `export_tiered_snapshot()` returns `TieredSnapshotEntry` list with scores and repeat-state.
8. Existing `ExerciseProgressStore` tests pass unchanged (TAC-DB-1).
9. `make -C packages/database check` passes.

## Verification / quality gates

- [ ] Unit tests for repeat-state transition matrix (all 6 cases)
- [ ] Unit tests for tiered progress summary computation
- [ ] Integration tests for tiered store lifecycle against real Neon PostgreSQL
- [ ] Integration test for idempotent replay
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] All files under 200 lines
- [ ] Negative-path tests: invalid repeat-state, unknown exercise_type, bad delta

## Edge cases

- Word with no scores at all (all default to 0): not in repeat, not fully completed, full sampling weight.
- Word with all positive scores: fully completed, not in repeat (unless manually corrupted).
- `apply_tiered_result` for a word not in the user's vocabulary: the existing `apply_score_delta_atomic` pattern handles this by upserting the score row. Repeat-state is only activated if conditions are met.
- Mode slug validation: empty string, whitespace-only.
- Concurrent `apply_tiered_result` calls for the same word: PostgreSQL transaction isolation handles this; event dedup prevents double-apply.

## Notes / risks

- **Risk**: The `abstract.py` file is currently 199 lines. Adding tiered abstract methods would exceed 200 lines.
  - **Mitigation**: If needed, extract tiered abstract methods into a `_tiered_abstract.py` mixin or a separate `AbstractTieredBackend` class. Alternatively, the tiered store can bypass the abstract backend and call `_neon_tiered.py` functions directly, keeping the tiered backend operations separate from the main abstract hierarchy. The developer should choose the approach that keeps all files under 200 lines.

- **Risk**: The atomic tiered replay requires reading scores after update within the same transaction.
  - **Mitigation**: Use `asyncpg`'s transaction context manager (already used in `atomic_apply_delta`). The pattern is: within `async with conn.transaction()`, apply score delta, read all participating scores, compute next repeat-state, update/delete repeat-state row, mark event applied.
