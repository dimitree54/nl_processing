---
Task ID: `T11`
Title: `Update e2e tests for new ExerciseProgressStore API signatures`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T10`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update all e2e tests for the database module to work with the refactored `ExerciseProgressStore` API: (1) update `conftest.py` fixture calls to pass `exercise_slugs` to `reset_database`, `drop_all_tables`, and `create_tables`, (2) update `test_exercise_progress.py` to pass `exercise_types` to `ExerciseProgressStore` constructor, use `source_word_id: int` for `increment`, and call `get_word_pairs_with_scores()` without arguments.

## Context (contract mapping)

- Requirements: Sprint request item 6 — "Testing Updates Required"
- Current: E2e tests construct `ExerciseProgressStore` without `exercise_types`, call `increment(Word, ...)`, and pass `exercise_types` to `get_word_pairs_with_scores`.
- New: Constructor requires `exercise_types`, `increment` takes `source_word_id: int`, `get_word_pairs_with_scores()` has no params.

## Preconditions

- T10 completed (integration tests pass — confirms backend + source code working against real DB).

## Non-goals

- Modifying source code.
- Modifying unit or integration tests.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/e2e/database/conftest.py`
- `tests/e2e/database/test_exercise_progress.py`

**FORBIDDEN — this task must NEVER touch:**
- Any source code files
- Unit or integration test files
- Any other module's tests

**Test scope:**
- Tests go in: `tests/e2e/database/`
- Test command: `doppler run -- uv run pytest tests/e2e/database/ -x -v`

## Touched surface (expected files / modules)

- `tests/e2e/database/conftest.py`
- `tests/e2e/database/test_exercise_progress.py`

## Dependencies and sequencing notes

- Depends on T10 (integration tests green = full backend verified).
- T12 depends on this (vulture whitelist is the final cleanup).

## Implementation steps (developer-facing)

### A. Update `conftest.py`

1. Define exercise slugs constant:
   ```python
   _EXERCISE_SLUGS = ["flashcard", "typing"]
   ```

2. Update `reset_database` call to pass `exercise_slugs`:
   ```python
   await reset_database(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
   ```

3. Update `drop_all_tables` call to pass `exercise_slugs`:
   ```python
   await drop_all_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
   ```

4. Update `create_tables` call to pass `exercise_slugs`:
   ```python
   await backend.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
   ```

### B. Update `test_exercise_progress.py`

5. **Update `ExerciseProgressStore` constructors** — all three tests create store instances. Add `exercise_types`:
   ```python
   store = ExerciseProgressStore(
       user_id=user_id,
       source_language=Language.NL,
       target_language=Language.RU,
       exercise_types=["flashcard", "typing"],
   )
   ```

6. **Update `increment` calls** — change from `Word` to word ID:
   - E2e tests add words via `DatabaseService.add_words()`, then call `increment` with `Word` objects. After refactoring, `increment` takes `source_word_id: int`.
   - The e2e test needs to look up word IDs. Use the backend to get word IDs, or use `DatabaseService.get_words()` to retrieve `WordPair` objects and then look up the source word ID.
   - Approach: After `_add_and_translate`, call `store.get_word_pairs_with_scores()` (which returns `ScoredWordPair` with `source_word_id`), then use those IDs for `increment`:
     ```python
     scored = await store.get_word_pairs_with_scores()
     id_by_form = {sp.pair.source.normalized_form: sp.source_word_id for sp in scored}
     await store.increment(id_by_form["tafel"], "flashcard", 1)
     ```

7. **Update `get_word_pairs_with_scores` calls** — remove arguments:
   - Old: `store.get_word_pairs_with_scores(["flashcard"])`
   - New: `store.get_word_pairs_with_scores()`

8. **Update `test_increment_and_retrieve_scores`**:
   - Get word IDs via `get_word_pairs_with_scores()` first.
   - Use IDs for `increment` calls.
   - Verify scores in the final `get_word_pairs_with_scores()` call.

9. **Update `test_missing_scores_default_to_zero`**:
   - `get_word_pairs_with_scores()` now returns scores for configured exercise types (flashcard, typing).
   - Update assertions to check both configured types.

10. **Update `test_scores_persist_across_store_instances`**:
    - Both `store_1` and `store_2` need `exercise_types`.
    - Get word ID from `store_1.get_word_pairs_with_scores()` before incrementing.
    - Use that ID for `increment`.

### C. Quality checks

11. Run linters:
    ```
    uv run ruff format tests/e2e/database/
    uv run ruff check tests/e2e/database/
    ```

12. Run e2e tests:
    ```
    doppler run -- uv run pytest tests/e2e/database/ -x -v
    ```

13. Check line counts.

## Production safety constraints (mandatory)

- **Database operations**: E2e tests connect to the **test database** via Doppler. The `db_ready` fixture resets and drops tables using advisory locks.
- **Resource isolation**: Advisory lock pattern (`pg_advisory_lock(12345)`) preserved exactly.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follows existing e2e test patterns.
- **No regressions**: All existing e2e tests updated to match new API.

## Error handling + correctness rules (mandatory)

- E2e tests verify end-to-end correctness (real DB, real OpenAI translation).
- No error suppression.

## Zero legacy tolerance rule (mandatory)

- All `Word` objects removed from `increment` calls.
- All `exercise_types` arguments removed from `get_word_pairs_with_scores` calls.
- All `ExerciseProgressStore` constructors include `exercise_types`.

## Acceptance criteria (testable)

1. `doppler run -- uv run pytest tests/e2e/database/ -x -v` — all tests pass.
2. All `ExerciseProgressStore` constructors pass `exercise_types`.
3. All `increment` calls use `source_word_id: int`.
4. All `get_word_pairs_with_scores` calls have no arguments.
5. All test files ≤ 200 lines.
6. `uv run ruff check tests/e2e/database/` — no errors.

## Verification / quality gates

- [x] E2e tests updated
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] All test files ≤ 200 lines

## Edge cases

- Word ID lookup via `get_word_pairs_with_scores`: depends on translations being completed. The `wait_for_translations` helper ensures this.
- Multiple store instances in `test_scores_persist_across_store_instances`: both must use the same `exercise_types`.

## Notes / risks

- **Risk**: E2e tests depend on real OpenAI translations completing. The existing `wait_for_translations` helper handles this with a timeout. No changes needed to the helper.
- **Risk**: `test_exercise_progress.py` (currently 95 lines) will grow slightly due to word ID lookup code. Estimate ~110 lines. Under 200.
