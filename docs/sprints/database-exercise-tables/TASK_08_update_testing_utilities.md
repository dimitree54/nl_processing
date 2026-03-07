---
Task ID: `T8`
Title: `Update testing.py for per-exercise-type table drop/reset`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T4`
Parallelizable: `yes, with T5–T6`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update `testing.py` so `drop_all_tables` and `reset_database` handle per-exercise-type score tables and the `applied_events` table. These test utilities must know about all tables to drop/recreate them in the correct FK-respecting order.

## Context (contract mapping)

- Requirements: Sprint request items 1, 3 — per-exercise tables + applied_events table
- Current: `testing.py` (104 lines) drops `user_word_exercise_scores_{src}_{tgt}` per pair.
- New: Must drop `user_word_exercise_scores_{src}_{tgt}_{slug}` for each (pair, slug) combo, and `applied_events_{src}_{tgt}` per pair.

## Preconditions

- T4 completed (NeonBackend's `create_tables` accepts `exercise_slugs`).

## Non-goals

- Updating integration/e2e test conftest files (T10/T11).
- Changing any source code outside `testing.py`.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database/testing.py` — test utilities

**FORBIDDEN — this task must NEVER touch:**
- Any source file other than `testing.py`
- Any test files (conftest updates are in T10/T11)
- Any other module

**Test scope:**
- No tests for `testing.py` itself. It's verified when integration/e2e tests call it (T10/T11).
- Linter check: `uv run ruff check nl_processing/database/testing.py`

## Touched surface (expected files / modules)

- `nl_processing/database/testing.py`

## Dependencies and sequencing notes

- Depends on T4 (backend `create_tables` signature change).
- T10 and T11 depend on this (integration/e2e fixtures call `drop_all_tables`/`reset_database`).

## Implementation steps (developer-facing)

1. **Update `drop_all_tables` signature**:
   - Add `exercise_slugs: list[str]` parameter.
   - New signature: `async def drop_all_tables(languages, pairs, exercise_slugs) -> None`.

2. **Update `drop_all_tables` implementation**:
   - Replace the per-pair score table drop:
     ```python
     # OLD:
     for src, tgt in pairs:
         await conn.execute(f"DROP TABLE IF EXISTS user_word_exercise_scores_{src}_{tgt}")
     # NEW:
     for src, tgt in pairs:
         for slug in exercise_slugs:
             await conn.execute(
                 f"DROP TABLE IF EXISTS user_word_exercise_scores_{src}_{tgt}_{slug}",
             )
     ```
   - Add `applied_events` table drop (before translations, after scores):
     ```python
     for src, tgt in pairs:
         await conn.execute(f"DROP TABLE IF EXISTS applied_events_{src}_{tgt}")
     ```
   - Drop order (FK-safe): score tables → applied_events → translations → user_words → words.

3. **Update `reset_database` signature and call**:
   - Add `exercise_slugs: list[str]` parameter.
   - Pass it to both `drop_all_tables` and `backend.create_tables`:
     ```python
     await drop_all_tables(languages, pairs, exercise_slugs)
     await backend.create_tables(languages, pairs, exercise_slugs)
     ```

4. **Line count check**: Currently 104 lines. Adding ~5 lines for exercise_slugs loops. Estimate ~110 lines. Under 200.

5. **Linter check**:
   ```
   uv run ruff format nl_processing/database/testing.py
   uv run ruff check nl_processing/database/testing.py
   ```

## Production safety constraints (mandatory)

- **Database operations**: `testing.py` functions are ONLY called from tests (module docstring says "NOT for production use"). They connect to the test database via `DATABASE_URL` (injected by Doppler in test runs).
- **Resource isolation**: Test utilities always use the test database. `drop_all_tables` is irreversible — only called in test fixtures.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extends existing utility functions.
- **No regressions**: Old callers of `drop_all_tables(languages, pairs)` will fail (missing `exercise_slugs`). They are updated in T10/T11.

## Error handling + correctness rules (mandatory)

- Existing `except Exception as exc: raise DatabaseError(str(exc)) from exc` pattern preserved.
- No errors silenced.

## Zero legacy tolerance rule (mandatory)

- Old `drop_all_tables(languages, pairs)` (2-param) is fully replaced by 3-param version.
- Old single-table drop loop is fully replaced by per-exercise-type loop.

## Acceptance criteria (testable)

1. `drop_all_tables(["nl", "ru"], [("nl", "ru")], ["flashcard", "typing"])` drops `user_word_exercise_scores_nl_ru_flashcard`, `user_word_exercise_scores_nl_ru_typing`, and `applied_events_nl_ru`.
2. `reset_database` passes `exercise_slugs` to both `drop_all_tables` and `create_tables`.
3. `uv run ruff check nl_processing/database/testing.py` — no errors.
4. File is ≤ 200 lines.

## Verification / quality gates

- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] File ≤ 200 lines

## Edge cases

- Empty `exercise_slugs` list: no score tables dropped/created. Valid for tests that don't use exercise scores.
- Exercise slugs with underscores: table names are valid PostgreSQL identifiers.

## Notes / risks

- **Risk**: Until T10 and T11 update the integration/e2e conftest files to pass `exercise_slugs`, those test fixtures will fail (wrong signature). This is expected and resolved in order.
