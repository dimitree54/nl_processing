---
Task ID: `T3`
Title: `Wire detailed-word DDL into create_tables() flow`
Sprint: `2026-03-13_detailed-words`
Module: `database`
Depends on: `T2`
Parallelizable: `no`
---

## Goal / value

Make `create_tables()` also create the `word_details_<src>_<tgt>` table. This is the only task that modifies existing files (`_queries.py` and `neon.py`), and the changes are minimal -- adding imports and a single function call each. Both files are at their line limits, so this task must also decompose them to stay under 200 lines.

## Context (contract mapping)

- Requirements: `packages/database/docs/module-spec.md` -- FR-5 (create_tables must also create detailed-word table)
- Critical constraint: `_queries.py` is at 188 lines, `neon.py` is at 187 lines. Both CANNOT grow.

## Preconditions

- T2 completed: `create_word_details_table()` DDL function exists in `_queries_detailed.py`.

## Non-goals

- No Neon CRUD methods (that's T4).
- No store implementation.
- No new test files -- existing table creation integration tests will validate the new table.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `src/nl_processing/database/backend/neon.py` -- minimal addition to `create_tables()` method
- `src/nl_processing/database/backend/_queries.py` -- decompose if needed to make room
- `src/nl_processing/database/backend/` -- new helper files for decomposition
- `tests/integration/database/` -- update table creation tests

**FORBIDDEN -- this task must NEVER touch:**
- `src/nl_processing/database/backend/abstract.py`
- `src/nl_processing/database/service.py`
- `src/nl_processing/core/` or any core package file
- Any other module

**Test scope:**
- Tests go in: `tests/integration/database/`
- Test command: `make check` (in `packages/database/`)

## Touched surface (expected files / modules)

**Files to modify:**
- `src/nl_processing/database/backend/neon.py` (187 lines) -- add import + 2-3 lines in `create_tables()`
- `tests/integration/database/test_table_creation.py` -- add test for detailed-word table creation

**Files potentially created for decomposition:**
- `src/nl_processing/database/backend/_neon_tables.py` (~30-50 lines) -- extract `create_tables` logic from `neon.py` if needed to make room

## Dependencies and sequencing notes

- Depends on T2 for `create_word_details_table()` DDL function in `_queries_detailed.py`.
- T4 depends on this: tables must be creatable before Neon CRUD tests can run.
- This is the ONLY task that modifies existing files, and the modifications are minimal.

## Third-party / library research (mandatory for any external dependency)

- No new dependencies. Uses existing `asyncpg` patterns.

## Implementation steps (developer-facing)

### Step 1: Assess line budgets

Current state:
- `neon.py`: 187 lines. Adding import + 2 lines in `create_tables()` = ~190 lines. Needs ~10 lines of headroom.
- `_queries.py`: 188 lines. No modifications needed to `_queries.py` itself -- the new DDL is in `_queries_detailed.py`.

### Step 2: Decompose `neon.py` to make room

Extract the `create_tables()` method body into a standalone async function in a new file:

**Create `src/nl_processing/database/backend/_neon_tables.py`** (~30-40 lines):
```python
"""Table creation logic extracted from NeonBackend."""
import asyncpg
from nl_processing.database.backend._queries import (
    CREATE_USER_WORDS, create_translations_table, create_words_table,
)
from nl_processing.database.backend._queries_detailed import create_word_details_table
from nl_processing.database.backend._neon_exercise import create_exercise_tables
from nl_processing.database.exceptions import DatabaseError

async def create_all_tables(
    conn: asyncpg.Connection,
    languages: list[str],
    pairs: list[tuple[str, str]],
    exercise_slugs: list[str],
) -> None:
    """Create all required database tables."""
    try:
        for lang in languages:
            await conn.execute(create_words_table(lang))
        for src, tgt in pairs:
            await conn.execute(create_translations_table(src, tgt))
        await conn.execute(CREATE_USER_WORDS)
        for src, tgt in pairs:
            await conn.execute(create_word_details_table(src, tgt))
    except asyncpg.PostgresError as exc:
        raise DatabaseError(str(exc)) from exc
    await create_exercise_tables(conn, pairs, exercise_slugs)
```

**Modify `neon.py`**: Replace the inline `create_tables()` body with a call to the extracted function:
```python
from nl_processing.database.backend._neon_tables import create_all_tables

# In create_tables():
async def create_tables(self, languages, pairs, exercise_slugs):
    conn = await self._connect()
    await create_all_tables(conn, languages, pairs, exercise_slugs)
    _logger.info("Created tables for languages=%s pairs=%s", languages, pairs)
```

This should reduce `neon.py` by ~10 lines (removing direct imports of DDL functions and the inline loop), netting enough headroom.

### Step 3: Verify line counts

After decomposition:
- `neon.py` should drop from 187 to ~178-180 lines (removed DDL imports + inline loops, added one import + one call).
- `_neon_tables.py` should be ~30-40 lines.
- `_queries.py` stays at 188 lines (unchanged).

### Step 4: Update integration test

Modify `tests/integration/database/test_table_creation.py` to verify the `word_details_nl_ru` table exists after `create_tables()`:
- Add a test that queries `information_schema.tables` for `word_details_nl_ru` after table creation.
- Or add a test that inserts and reads from the detailed-word table after creation.

### Step 5: Run `make check` and verify green.

## Production safety constraints (mandatory)

- **Database operations**: Integration tests run against the testing Neon database only (via `DATABASE_URL` from Doppler).
- The `CREATE TABLE IF NOT EXISTS` DDL is idempotent -- safe to run in any environment.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the exact same extraction pattern used for `_neon_exercise.py` (extracted from `neon.py`).
- **No regressions**: Existing `create_tables()` behavior is preserved exactly. The only addition is creating the `word_details_<src>_<tgt>` table.
- **Line budget**: After this task, `neon.py` must be at or below 185 lines.

## Error handling + correctness rules (mandatory)

- DDL execution errors are caught and re-raised as `DatabaseError` (same pattern as existing code).
- `CREATE TABLE IF NOT EXISTS` semantics ensure idempotent behavior.

## Zero legacy tolerance rule (mandatory)

- The inline `create_tables()` DDL loop in `neon.py` is replaced by a call to `_neon_tables.py`. The old inline code is removed.

## Acceptance criteria (testable)

1. `neon.py` is at or below 185 lines.
2. `_neon_tables.py` exists and contains the extracted `create_all_tables()` function.
3. `create_tables(languages=["nl", "ru"], pairs=[("nl", "ru")], exercise_slugs=["flashcard"])` now also creates `word_details_nl_ru` table.
4. Integration test verifies `word_details_nl_ru` table exists after `create_tables()`.
5. All existing tests continue to pass unchanged.
6. `make check` passes in `packages/database/`.
7. No file exceeds 200 lines.

## Verification / quality gates

- [x] Integration test added/updated for detailed-word table creation
- [x] Linters/formatters pass (`make check`)
- [x] No new warnings introduced
- [x] All files under 200 lines
- [x] Existing tests pass without modification

## Edge cases

- Running `create_tables()` twice must be safe (IF NOT EXISTS semantics).
- Table creation with different pairs (e.g., `("nl", "en")`) must create `word_details_nl_en`.

## Notes / risks

- **Risk**: Extracting `create_tables()` body changes import structure in `neon.py`.
  - **Mitigation**: The extraction follows the proven `_neon_exercise.py` pattern. Imports are rearranged, not removed.
- **Risk**: `_queries.py` at 188 lines is not modified, but this is acceptable since the new DDL lives in `_queries_detailed.py`.
  - **Mitigation**: No action needed. `_queries.py` stays unchanged.
- **Critical**: The `testing.py` module's `drop_all_tables()` does NOT need to know about `word_details_<src>_<tgt>` yet -- that's deferred to T7.
