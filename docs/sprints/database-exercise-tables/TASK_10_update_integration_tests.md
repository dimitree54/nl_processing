---
Task ID: `T10`
Title: `Update integration tests for per-exercise-type tables`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T8, T9`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update all integration tests to work with the per-exercise-type table structure: (1) update `conftest.py` fixture to pass `exercise_slugs` to `create_tables`, (2) update `test_exercise_scores.py` to call backend methods with new signatures (no `exercise_type` param; table name includes exercise slug), (3) update `test_table_creation.py` expected tables list and calls to pass `exercise_slugs`, (4) update `test_neon_backend.py` if affected.

## Context (contract mapping)

- Requirements: Sprint request items 1, 3, 6
- Current: Integration tests use `create_tables(languages, pairs)` and `increment_user_exercise_score(table, user_id, word_id, exercise_type, delta)`.
- New: `create_tables(languages, pairs, exercise_slugs)` and `increment_user_exercise_score(table, user_id, word_id, delta)`.

## Preconditions

- T8 completed (testing.py updated with `exercise_slugs`).
- T9 completed (unit tests pass — source code is verified working).

## Non-goals

- Modifying source code.
- Modifying e2e tests (T11).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/integration/database/conftest.py`
- `tests/integration/database/test_exercise_scores.py`
- `tests/integration/database/test_table_creation.py`
- `tests/integration/database/test_neon_backend.py` (if needed)

**FORBIDDEN — this task must NEVER touch:**
- Any source code files
- Unit tests or e2e tests
- Any other module's tests

**Test scope:**
- Tests go in: `tests/integration/database/`
- Test command: `doppler run -- uv run pytest tests/integration/database/ -x -v`

## Touched surface (expected files / modules)

- `tests/integration/database/conftest.py`
- `tests/integration/database/test_exercise_scores.py`
- `tests/integration/database/test_table_creation.py`
- `tests/integration/database/test_neon_backend.py` (minor, if `create_tables` calls changed)

## Dependencies and sequencing notes

- Depends on T8 (testing.py) and T9 (unit tests green = source code verified).
- T11 depends on this (e2e tests follow similar fixture patterns).

## Implementation steps (developer-facing)

### A. Update `conftest.py`

1. Define exercise slugs constant:
   ```python
   _EXERCISE_SLUGS = ["flashcard", "typing"]
   ```

2. Update `neon_backend` fixture's `create_tables` call:
   ```python
   await backend.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
   ```

### B. Update `test_exercise_scores.py`

3. **Update all `increment_user_exercise_score` calls**:
   - Old: `neon_backend.increment_user_exercise_score("nl_ru", user_id, word_id, "flashcard", 1)`
   - New: `neon_backend.increment_user_exercise_score("nl_ru_flashcard", user_id, word_id, 1)`
   - The table name now includes the exercise slug. Remove the `exercise_type` parameter.

4. **Update all `get_user_exercise_scores` calls**:
   - Old: `neon_backend.get_user_exercise_scores("nl_ru", user_id, [word_id], ["flashcard", "typing"])`
   - New: Call per exercise type table:
     ```python
     flashcard_scores = await neon_backend.get_user_exercise_scores("nl_ru_flashcard", user_id, [word_id])
     typing_scores = await neon_backend.get_user_exercise_scores("nl_ru_typing", user_id, [word_id])
     ```
   - Update assertions: returned dicts no longer have `exercise_type` key.

5. **Update `test_get_user_exercise_scores_returns_correct_scores`** specifically:
   - This test increments "flashcard" twice and "typing" once, then fetches both.
   - New approach: fetch from each table separately, verify counts.

6. **Update `test_score_increments_correctly`**: Change table to `"nl_ru_multiple_choice"` (was using `"nl_ru"` with `exercise_type="multiple_choice"`).

7. **Update `test_score_decrements_correctly`**: Change table to `"nl_ru_typing"`.

### C. Update `test_table_creation.py`

8. **Update `_EXPECTED_TABLES`**:
   ```python
   _EXPECTED_TABLES = [
       "words_nl",
       "words_ru",
       "translations_nl_ru",
       "user_words",
       "user_word_exercise_scores_nl_ru_flashcard",
       "user_word_exercise_scores_nl_ru_typing",
       "applied_events_nl_ru",
   ]
   ```

9. **Update `_ISO_EXPECTED`** similarly for de/fr test tables:
   ```python
   _ISO_EXPECTED = [
       "words_de",
       "words_fr",
       "translations_de_fr",
       "user_words",
       "user_word_exercise_scores_de_fr_flashcard",
       "user_word_exercise_scores_de_fr_typing",
       "applied_events_de_fr",
   ]
   ```

10. **Add exercise slugs constants**:
    ```python
    _EXERCISE_SLUGS = ["flashcard", "typing"]
    ```

11. **Update all `create_tables` calls** to pass `_EXERCISE_SLUGS`:
    ```python
    await backend.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
    ```

12. **Update all `drop_all_tables` and `reset_database` calls** to pass exercise slugs:
    ```python
    await drop_all_tables(_ISO_LANGUAGES, _ISO_PAIRS, _EXERCISE_SLUGS)
    await reset_database(_ISO_LANGUAGES, _ISO_PAIRS, _EXERCISE_SLUGS)
    ```

### D. Update `test_neon_backend.py`

13. **Minimal changes**: This file tests CRUD operations (add_word, get_word, add_translation_link, add_user_word, get_user_words). These are unaffected by exercise table changes. No changes needed unless `create_tables` is called directly in this file (it's not — it uses the `neon_backend` fixture from conftest).

### E. Quality checks

14. Run linters:
    ```
    uv run ruff format tests/integration/database/
    uv run ruff check tests/integration/database/
    ```

15. Run integration tests:
    ```
    doppler run -- uv run pytest tests/integration/database/ -x -v
    ```

16. Check line counts for all modified files.

## Production safety constraints (mandatory)

- **Database operations**: Integration tests connect to the **test database** via Doppler-injected `DATABASE_URL`. Never the production database.
- **Resource isolation**: Advisory locks (`pg_advisory_lock_shared(12345)`) ensure serialization with lifecycle tests. Pattern preserved.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follows existing integration test patterns.
- **No regressions**: All existing tests updated to match new API.

## Error handling + correctness rules (mandatory)

- Tests verify correct behavior, not error suppression.
- Empty input tests updated for new signatures.

## Zero legacy tolerance rule (mandatory)

- All references to old single exercise score table (`user_word_exercise_scores_nl_ru`) removed.
- All calls with `exercise_type` parameter removed.

## Acceptance criteria (testable)

1. `doppler run -- uv run pytest tests/integration/database/ -x -v` — all tests pass.
2. `test_create_tables_creates_all_expected_tables` checks for per-exercise-type tables.
3. `test_exercise_scores.py` uses per-exercise-type table names in all backend calls.
4. No references to old single `user_word_exercise_scores_{src}_{tgt}` table remain.
5. All test files ≤ 200 lines.
6. `uv run ruff check tests/integration/database/` — no errors.

## Verification / quality gates

- [x] Integration tests updated
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] All test files ≤ 200 lines

## Edge cases

- Advisory lock interaction: lifecycle test drops/recreates tables including per-exercise-type ones. Lock pattern unchanged.
- Isolated language tests (de/fr): must also use per-exercise-type tables with exercise_slugs.

## Notes / risks

- **Risk**: `test_exercise_scores.py` currently has a test (`test_get_user_exercise_scores_returns_correct_scores`) that fetches scores for multiple exercise types in one call. With per-exercise tables, this requires two separate calls. The test structure changes but the verification logic is equivalent.
- **Risk**: `test_table_creation.py` line count (currently 125). Adding exercise_slugs and more expected tables may push to ~135. Under 200.
