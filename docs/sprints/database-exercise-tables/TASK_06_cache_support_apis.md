---
Task ID: `T6`
Title: `Add cache-support APIs: export_remote_snapshot and apply_score_delta`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T5`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Add two new methods to `ExerciseProgressStore` to support the planned `database_cache` module: (1) `export_remote_snapshot()` — returns translated word pairs with stable remote IDs + scores for configured exercises, and (2) `apply_score_delta(event_id, source_word_id, exercise_type, delta)` — idempotent score increment using `event_id` as idempotency key via the `applied_events` table.

## Context (contract mapping)

- Requirements: Sprint request item 3 — "Cache Support APIs (New)"
- `export_remote_snapshot()` is essentially `get_word_pairs_with_scores()` but the return type should include the word's remote database ID for stable cache references.
- `apply_score_delta()` wraps `increment()` with idempotency: checks `applied_events` before applying, marks event as applied after.

## Preconditions

- T5 completed (ExerciseProgressStore refactored with new constructor and method signatures).
- T4 completed (backend supports `check_event_applied` and `mark_event_applied`).

## Non-goals

- Implementing the `database_cache` module itself.
- Modifying `models.py` beyond what's needed for snapshot data.
- Updating tests (T9).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database/exercise_progress.py` — add new methods
- `nl_processing/database/models.py` — if a new model is needed for snapshot data (optional; may reuse `ScoredWordPair` if it already has word IDs)

**FORBIDDEN — this task must NEVER touch:**
- Backend files (already support event tracking from T4)
- Test files (T9)
- Any other module

**Test scope:**
- No tests run during this task (tests added in T9).
- Linter check: `uv run ruff check nl_processing/database/exercise_progress.py`

## Touched surface (expected files / modules)

- `nl_processing/database/exercise_progress.py`
- `nl_processing/database/models.py` (only if new model needed)

## Dependencies and sequencing notes

- Depends on T5 (ExerciseProgressStore must have new constructor/methods in place).
- T9 depends on this (unit tests for new APIs).

## Implementation steps (developer-facing)

1. **Assess model needs for `export_remote_snapshot`**:
   - Current `ScoredWordPair` has `pair: WordPair` and `scores: dict[str, int]`.
   - `WordPair` has `source: Word` and `target: Word`.
   - `Word` has `normalized_form`, `word_type`, `language` — but no `id` field.
   - The snapshot needs stable remote IDs. The backend's `get_user_words` returns rows with `source_id` and `target_id`.
   - Option A: Add a `RemoteScoredWordPair` model to `models.py` that includes `source_word_id: int`.
   - Option B: Reuse `ScoredWordPair` and include the ID in the return structure.
   - **Decision**: Add `source_word_id: int` field to `ScoredWordPair` (or create a new model). Since `ScoredWordPair` is used by `get_word_pairs_with_scores` too, adding `source_word_id` there is clean and backwards-compatible (Pydantic model, adding a field).

2. **Update `ScoredWordPair` in `models.py`**:
   - Add `source_word_id: int` field:
     ```python
     class ScoredWordPair(BaseModel):
         pair: WordPair
         scores: dict[str, int]
         source_word_id: int
     ```
   - This requires all constructors of `ScoredWordPair` to provide the ID. Update `get_word_pairs_with_scores` (in T5's code) to pass `source_word_id=wid`.

3. **Implement `export_remote_snapshot`**:
   ```python
   async def export_remote_snapshot(self) -> list[ScoredWordPair]:
       """Return translated word pairs with stable remote IDs and scores.

       Identical to get_word_pairs_with_scores() — provided as a named
       entry point for the database_cache module.
       """
       return await self.get_word_pairs_with_scores()
   ```
   - This is a thin wrapper for semantic clarity. The `source_word_id` field on `ScoredWordPair` provides the stable remote ID.

4. **Implement `apply_score_delta`**:
   ```python
   async def apply_score_delta(
       self,
       event_id: str,
       source_word_id: int,
       exercise_type: str,
       delta: int,
   ) -> None:
       """Idempotent score increment using event_id for deduplication.

       If event_id has already been applied, this is a no-op.
       Otherwise, increments the score and records the event.
       Raises ValueError if exercise_type not in configured set or delta invalid.
       """
       if exercise_type not in self._score_tables:
           msg = f"exercise_type '{exercise_type}' not in configured set: {list(self._score_tables)}"
           raise ValueError(msg)
       events_table = f"{self._source_language.value}_{self._target_language.value}"
       already_applied = await self._backend.check_event_applied(events_table, event_id)
       if already_applied:
           return
       await self.increment(source_word_id, exercise_type, delta)
       await self._backend.mark_event_applied(events_table, event_id)
   ```

5. **Update `get_word_pairs_with_scores` to include `source_word_id`**:
   - In the result construction, pass `source_word_id=wid`:
     ```python
     result.append(ScoredWordPair(pair=pair, scores=scores, source_word_id=wid))
     ```

6. **Line count check**: Adding ~25 lines for two new methods. File was ~134 after T5. Estimate ~159 lines. Under 200.

7. **Linter check**:
   ```
   uv run ruff format nl_processing/database/exercise_progress.py nl_processing/database/models.py
   uv run ruff check nl_processing/database/exercise_progress.py nl_processing/database/models.py
   ```

## Production safety constraints (mandatory)

- **Database operations**: No DB connections during this task (code only).
- **Resource isolation**: N/A.
- **Migration preparation**: N/A (applied_events table DDL already handled in T2/T4).

## Anti-disaster constraints (mandatory)

- **Reuse before build**: `export_remote_snapshot` reuses `get_word_pairs_with_scores`. `apply_score_delta` reuses `increment`.
- **No regressions**: Adding a field to `ScoredWordPair` is backwards-compatible for readers (Pydantic). Constructors must be updated (done here and in T5's `get_word_pairs_with_scores`).

## Error handling + correctness rules (mandatory)

- `apply_score_delta` validates `exercise_type` membership.
- `apply_score_delta` delegates delta validation to `increment` (which validates ±1).
- If `check_event_applied` raises `DatabaseError`, it propagates — not silenced.
- If `mark_event_applied` fails after `increment` succeeds: the score is incremented but event not marked. On retry, the event will not be found as applied and the score will be incremented again. **This is a known limitation** — true atomic idempotency would require a database transaction. Document this as a risk.

## Zero legacy tolerance rule (mandatory)

- No old code paths removed in this task (purely additive).
- No dead code introduced.

## Acceptance criteria (testable)

1. `ScoredWordPair` has a `source_word_id: int` field.
2. `get_word_pairs_with_scores()` returns `ScoredWordPair` with `source_word_id` populated.
3. `export_remote_snapshot()` returns the same result as `get_word_pairs_with_scores()`.
4. `apply_score_delta(event_id, source_word_id, exercise_type, delta)` increments score on first call.
5. `apply_score_delta` with the same `event_id` a second time is a no-op (idempotent).
6. `apply_score_delta` raises `ValueError` for unknown `exercise_type`.
7. `uv run ruff check nl_processing/database/exercise_progress.py nl_processing/database/models.py` — no errors.
8. Both files are ≤ 200 lines.

## Verification / quality gates

- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Files ≤ 200 lines

## Edge cases

- `apply_score_delta` called with `delta=0`: `increment` will raise `ValueError` (delta must be ±1). This propagates correctly.
- Concurrent `apply_score_delta` with same `event_id`: race condition possible (both check, both see not-applied, both apply). Acceptable for the current use case (single-user CLI/bot). Document as known limitation.
- `export_remote_snapshot` on user with no words: returns empty list (same as `get_word_pairs_with_scores`).

## Notes / risks

- **Risk**: `apply_score_delta` is not truly atomic (check + increment + mark are three separate operations). For production-grade idempotency, a database transaction with `SELECT FOR UPDATE` or a combined INSERT would be needed. The current implementation is sufficient for the planned `database_cache` module's single-user, sequential replay pattern.
- **Risk**: Adding `source_word_id` to `ScoredWordPair` changes the model used by `sampling/service.py`. Pydantic v2 handles extra fields gracefully, but the sampling module constructs `ScoredWordPair` indirectly via `get_word_pairs_with_scores` — which this task updates. Sampling tests will break (they don't pass `source_word_id` when constructing `ScoredWordPair`), but sampling tests are NOT run in this sprint.
