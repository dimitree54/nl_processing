---
Task ID: `T5`
Title: `Refactor ExerciseProgressStore — new constructor, changed increment/get_word_pairs_with_scores`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T4`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Refactor `ExerciseProgressStore` to: (1) require `exercise_types: list[str]` in the constructor, (2) change `increment()` to take `source_word_id: int` instead of `source_word: Word`, (3) make `increment()` validate that the `exercise_type` belongs to the configured set, (4) remove the `exercise_types` parameter from `get_word_pairs_with_scores()` (use the configured set instead), and (5) compute per-exercise-type table names from the configured exercise types.

## Context (contract mapping)

- Requirements: Sprint request item 2 — "ExerciseProgressStore Constructor Change"
- Current: Constructor takes `(user_id, source_language, target_language)` — no `exercise_types`.
- Current: `increment(source_word: Word, exercise_type, delta)` looks up word ID from backend.
- Current: `get_word_pairs_with_scores(exercise_types)` takes the list as a parameter.
- New: Constructor requires `exercise_types`. `increment` takes `source_word_id: int` directly. `get_word_pairs_with_scores()` uses `self._exercise_types`.

## Preconditions

- T4 completed (NeonBackend implements updated abstract methods).

## Non-goals

- Adding cache-support APIs (`export_remote_snapshot`, `apply_score_delta`) — that's T6.
- Updating tests — that's T9.
- Updating the sampling module — FORBIDDEN (separate sprint).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database/exercise_progress.py` — ExerciseProgressStore refactoring

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/sampling/service.py` — downstream consumer (separate sprint)
- Any test files (T9)
- Any backend files (done in T2-T4)
- Any other module

**Test scope:**
- No tests run during this task (tests are updated in T9).
- Linter check: `uv run ruff check nl_processing/database/exercise_progress.py`

## Touched surface (expected files / modules)

- `nl_processing/database/exercise_progress.py` (135 lines currently)

## Dependencies and sequencing notes

- Depends on T4 (backend must support new method signatures).
- T6 depends on this (cache-support APIs are added to `ExerciseProgressStore`).
- T9 depends on this (unit tests must be updated for new signatures).
- **DOWNSTREAM IMPACT**: `nl_processing/sampling/service.py` creates `ExerciseProgressStore` without `exercise_types` (line 28) and passes `self._exercise_types` to `get_word_pairs_with_scores` (line 50). After this task, sampling will break. This is documented; sampling must be updated in a separate sprint.

## Implementation steps (developer-facing)

1. **Update constructor**:
   - Add `exercise_types: list[str]` as a keyword argument.
   - Validate non-empty: `if not exercise_types: raise ValueError("exercise_types must be non-empty")`.
   - Store: `self._exercise_types = exercise_types`.
   - Compute score table names: `self._score_tables = {et: f"{src}_{tgt}_{et}" for et in exercise_types}`.
   - Remove old `self._score_table = f"{src}_{tgt}"`.
   - Remove `self._source_table = f"words_{src}"` (no longer needed — `increment` takes word ID directly).
   - Keep import of `Word` for `_word_from_row` helper (still used internally by `get_word_pairs_with_scores`).

2. **Update `increment` method**:
   - Change signature: `async def increment(self, source_word_id: int, exercise_type: str, delta: int) -> None`
   - Add exercise_type validation: `if exercise_type not in self._score_tables: raise ValueError(f"exercise_type '{exercise_type}' not in configured set: {list(self._score_tables)}")`
   - Remove word lookup (no longer needed — caller passes word ID directly).
   - Remove `DatabaseError` raise for missing word.
   - Call backend with per-exercise table: `await self._backend.increment_user_exercise_score(self._score_tables[exercise_type], self._user_id, source_word_id, delta)`

3. **Update `get_word_pairs_with_scores`**:
   - Remove `exercise_types` parameter. New signature: `async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]`
   - Use `self._exercise_types` instead.
   - Iterate over `self._score_tables` to get scores per exercise type:
     ```python
     scores_by_word: dict[int, dict[str, int]] = {}
     for exercise_type, table in self._score_tables.items():
         score_rows = await self._backend.get_user_exercise_scores(
             table, self._user_id, source_word_ids,
         )
         for score_row in score_rows:
             wid = int(score_row["source_word_id"])
             scores_by_word.setdefault(wid, {})[exercise_type] = int(score_row["score"])
     ```
   - Build result with defaults for each exercise type:
     ```python
     scores = {et: word_scores.get(et, 0) for et in self._exercise_types}
     ```

4. **Clean up imports**:
   - Remove `Word` from imports if no longer used anywhere in the file. Check: `_word_from_row` still uses `Word` and `PartOfSpeech` for constructing return objects. Keep them.
   - Keep `Language`, `PartOfSpeech`, `Word` imports (used by `_word_from_row`).
   - `DatabaseError` may no longer be needed in this file (was used for "word not found" in old `increment`). Check if any other method raises it. If not, remove the import.

5. **Line count check**: Currently 135 lines. Removing word lookup from `increment` (saves ~7 lines). Adding exercise_type validation (adds ~3 lines). Adding loop in `get_word_pairs_with_scores` (adds ~5 lines). Constructor changes (net ~3 lines). Estimate ~134 lines. Well under 200.

6. **Linter check**:
   ```
   uv run ruff format nl_processing/database/exercise_progress.py
   uv run ruff check nl_processing/database/exercise_progress.py
   ```

## Production safety constraints (mandatory)

- **Database operations**: No DB connections during this task (code change only, no tests run).
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Refactors existing class, no new files.
- **No regressions**: Tests will fail until T9 updates them. This is expected.

## Error handling + correctness rules (mandatory)

- `ValueError` raised for empty `exercise_types` in constructor.
- `ValueError` raised for `exercise_type` not in configured set during `increment`.
- `ValueError` still raised for invalid `delta` (not +1 or -1).
- `DatabaseError` import may be removed if no longer used in this file.

## Zero legacy tolerance rule (mandatory)

- Old `self._score_table` (single table) is fully replaced by `self._score_tables` (dict per exercise type).
- Old `increment(source_word: Word, ...)` signature is fully replaced.
- Old word-lookup logic in `increment` is fully removed (caller provides word ID).
- Old `get_word_pairs_with_scores(exercise_types)` param is removed.

## Acceptance criteria (testable)

1. Constructor requires `exercise_types: list[str]`; raises `ValueError` if empty.
2. `increment(source_word_id: int, exercise_type: str, delta: int)` — takes int, not `Word`.
3. `increment` raises `ValueError` if `exercise_type` not in configured set.
4. `get_word_pairs_with_scores()` takes no arguments; returns scores for configured exercise types.
5. Per-exercise-type score tables are used (e.g., `nl_ru_flashcard` instead of `nl_ru`).
6. `uv run ruff check nl_processing/database/exercise_progress.py` — no errors.
7. File is ≤ 200 lines.

## Verification / quality gates

- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] File ≤ 200 lines

## Edge cases

- Single exercise type in list → only one score table used.
- Multiple exercise types → multiple score tables queried in `get_word_pairs_with_scores`.
- Exercise type with underscores (`listen_and_type`) → table name includes it. Valid.

## Notes / risks

- **Risk**: `sampling/service.py` will break (documented). NOT fixed in this sprint.
- **Risk**: `_word_from_row` and `_row_to_word_pair` private helpers remain unchanged. They are correct — the backend `get_user_words` returns the same row structure.
