---
Task ID: `T7`
Title: `Extend testing.py with detailed-word table drop/reset helpers`
Sprint: `2026-03-13_detailed-words`
Module: `database`
Depends on: `T4`
Parallelizable: `yes, with T5, T6`
---

## Goal / value

Update the test-only `drop_all_tables()` and `reset_database()` helpers in `testing.py` to also drop `word_details_<src>_<tgt>` tables. Without this, test teardown leaves orphaned detailed-word tables, and the e2e fixtures cannot fully reset the database.

## Context (contract mapping)

- Requirements: `packages/database/docs/module-spec.md` -- FR-5 (create_tables includes detailed-word table)
- Pattern reference: `src/nl_processing/database/testing.py` (existing test helpers, 111 lines)

## Preconditions

- T3 completed: `create_tables()` creates `word_details_<src>_<tgt>` table (so `reset_database()` will recreate it).

## Non-goals

- No new test files -- this updates the existing `testing.py` helper.
- No functional code changes.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `src/nl_processing/database/testing.py` -- add detailed-word table drop

**FORBIDDEN -- this task must NEVER touch:**
- Any other source file
- `src/nl_processing/core/` or any core package file
- Any other module

**Test scope:**
- Tests go in: existing tests already exercise `testing.py` via fixtures
- Test command: `make check` (in `packages/database/`)

## Touched surface (expected files / modules)

**Files to modify:**
- `src/nl_processing/database/testing.py` (currently 111 lines) -- add ~3-5 lines for dropping `word_details_<src>_<tgt>` tables

## Dependencies and sequencing notes

- Depends on T3 (table exists in schema) and T4 (knowing the table structure).
- Can run in parallel with T5 and T6.
- The e2e conftest (`db_ready` fixture) calls `drop_all_tables()` and `reset_database()`, so this update makes those fixtures work correctly with the new table.

## Third-party / library research (mandatory for any external dependency)

- No new dependencies.

## Implementation steps (developer-facing)

1. **Modify `src/nl_processing/database/testing.py`:**

   In `drop_all_tables()`, add dropping of `word_details_<src>_<tgt>` tables **before** dropping `translations_<src>_<tgt>` tables (since `word_details` has a FK to `words_<src>`, it must be dropped before `words_<src>`):

   Current drop order:
   1. `user_word_exercise_scores_{src}_{tgt}_{slug}`
   2. `applied_events_{src}_{tgt}`
   3. `translations_{src}_{tgt}`
   4. `user_words`
   5. `words_{lang}`

   New drop order (add step between 2 and 3):
   1. `user_word_exercise_scores_{src}_{tgt}_{slug}`
   2. `applied_events_{src}_{tgt}`
   3. **`word_details_{src}_{tgt}`** (NEW -- must drop before `words_<src>` due to FK)
   4. `translations_{src}_{tgt}`
   5. `user_words`
   6. `words_{lang}`

   Add approximately 3 lines:
   ```python
   for src, tgt in pairs:
       await conn.execute(
           f"DROP TABLE IF EXISTS word_details_{src}_{tgt}",  # noqa: S608
       )
   ```

2. **Verify line count**: `testing.py` goes from 111 to ~114 lines. Well under 200.

3. **Run `make check`** in `packages/database/` and verify green.

## Production safety constraints (mandatory)

- **Database operations**: `drop_all_tables()` is a **test-only** utility. It is never imported from production code. It only runs against the testing database.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the exact same `DROP TABLE IF EXISTS` pattern already used for other tables.
- **No regressions**: Adding a drop for a new table does not affect existing table drops.

## Error handling + correctness rules (mandatory)

- `DROP TABLE IF EXISTS` is safe even if the table doesn't exist (e.g., if tests run against a schema without T3's changes).
- Errors are caught by the existing `except Exception` block in `drop_all_tables()`.

## Zero legacy tolerance rule (mandatory)

- N/A -- this is a purely additive change to an existing helper.

## Acceptance criteria (testable)

1. `drop_all_tables(["nl", "ru"], [("nl", "ru")], ["flashcard"])` also drops `word_details_nl_ru`.
2. `reset_database(["nl", "ru"], [("nl", "ru")], ["flashcard"])` drops and recreates all tables including `word_details_nl_ru`.
3. `testing.py` stays under 200 lines (expected ~114 lines).
4. Existing e2e tests continue to pass (fixtures use these helpers).
5. `make check` passes in `packages/database/`.

## Verification / quality gates

- [x] Existing e2e tests pass (they use `drop_all_tables` / `reset_database`)
- [x] Linters/formatters pass (`make check`)
- [x] No new warnings introduced
- [x] `testing.py` under 200 lines

## Edge cases

- If `word_details_nl_ru` doesn't exist (e.g., running against old schema), `DROP TABLE IF EXISTS` is a no-op.
- FK ordering: `word_details` must be dropped before `words_<lang>` since it references `words_<lang>.id`.

## Notes / risks

- **Risk**: None -- this is a 3-line addition to a well-understood helper.
