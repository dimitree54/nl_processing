---
Task ID: `T4`
Title: `Implement Neon backend methods for detailed-word CRUD with integration tests`
Sprint: `2026-03-13_detailed-words`
Module: `database`
Depends on: `T3`
Parallelizable: `no`
---

## Goal / value

Implement the concrete `asyncpg` backend for detailed-word get and upsert operations, following the `_neon_exercise.py` extraction pattern. After this task, detailed-word rows can be read and written to Neon PostgreSQL, and the implementation is fully integration-tested.

## Context (contract mapping)

- Requirements: `packages/database/docs/module-spec.md` -- FR-12 (persist pair-specific detailed rows), FR-14 (reject invalid data)
- Pattern reference: `src/nl_processing/database/backend/_neon_exercise.py` (extracted Neon operations)
- Pattern reference: `src/nl_processing/database/backend/_neon_words.py` (word CRUD operations)

## Preconditions

- T2 completed: `_queries_detailed.py` with SQL templates and `_abstract_detailed.py` with abstract methods exist.
- T3 completed: `create_tables()` creates the `word_details_<src>_<tgt>` table, so integration tests can run.

## Non-goals

- No `DetailedWordStore` public API (that's T5).
- No modification to `neon.py` (already at limit; CRUD lives in extracted module).
- No mock backend yet (that's T5).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `src/nl_processing/database/backend/` -- new file `_neon_detailed.py`
- `tests/integration/database/` -- new test file

**FORBIDDEN -- this task must NEVER touch:**
- `src/nl_processing/database/backend/neon.py` (187 lines, already at limit)
- `src/nl_processing/database/backend/abstract.py` (existing)
- `src/nl_processing/core/` or any core package file
- Any other module

**Test scope:**
- Tests go in: `tests/integration/database/`
- Test command: `make check` (in `packages/database/`)

## Touched surface (expected files / modules)

**New files to create:**
- `src/nl_processing/database/backend/_neon_detailed.py` (~70-100 lines) -- Concrete asyncpg implementations
- `tests/integration/database/test_detailed_words.py` (~100-150 lines) -- Integration tests against real Neon

## Dependencies and sequencing notes

- Depends on T2 for SQL query templates.
- Depends on T3 for table creation (integration tests need the table to exist).
- T5 depends on this task for the concrete backend.
- T7 depends on this task for knowing what tables to drop.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncpg` -- already used throughout the backend. No new version needed.
  - `conn.fetch(query, *args)` returns `list[Record]`
  - `conn.execute(query, *args)` for DML
  - `conn.fetchrow(query, *args)` returns single `Record | None`
  - JSON payloads are passed as strings and stored in JSONB columns.
- No new dependencies.

## Implementation steps (developer-facing)

1. **Create `src/nl_processing/database/backend/_neon_detailed.py`:**

   Following the `_neon_exercise.py` pattern, implement standalone async functions:

   ```python
   async def get_word_details(
       conn: asyncpg.Connection,
       src: str,
       tgt: str,
       source_word_ids: list[int],
   ) -> list[dict[str, str | int]]:
       """Fetch detailed-word rows for the given source word IDs."""
       if not source_word_ids:
           return []
       query = get_word_details_query(src, tgt)
       try:
           rows = await conn.fetch(query, source_word_ids)
       except asyncpg.PostgresError as exc:
           raise DatabaseError(str(exc)) from exc
       return [dict(row) for row in rows]

   async def upsert_word_detail(
       conn: asyncpg.Connection,
       src: str,
       tgt: str,
       source_word_id: int,
       word_type: str,
       schema_key: str,
       schema_version: int,
       payload: str,
   ) -> None:
       """Upsert one detailed-word row."""
       query = upsert_word_detail_query(src, tgt)
       try:
           await conn.execute(
               query, source_word_id, word_type, schema_key,
               schema_version, payload,
           )
       except asyncpg.PostgresError as exc:
           raise DatabaseError(str(exc)) from exc
   ```

   Import SQL templates from `_queries_detailed.py` and `DatabaseError` from `exceptions.py`.

2. **Create `tests/integration/database/test_detailed_words.py`:**

   Use the existing `neon_backend` fixture pattern from `conftest.py`:

   - **Test setup**: Use `neon_backend` fixture which creates tables. Since T3 wired detailed-word table creation into `create_tables()`, the `word_details_nl_ru` table will exist.
   - **Test `upsert_word_detail`**: Insert a canonical word via `add_word()`, then upsert a detail row. Verify no error.
   - **Test `get_word_details`**: After upserting a detail row, fetch it back. Verify `source_word_id`, `word_type`, `schema_key`, `schema_version`, and `payload` round-trip correctly.
   - **Test upsert overwrites**: Upsert same (source_word_id, word_type) with different payload/version. Verify the row is updated, not duplicated.
   - **Test `get_word_details` with empty IDs**: Verify returns `[]`.
   - **Test `get_word_details` with non-existent IDs**: Verify returns `[]`.
   - **Test FK constraint**: Attempting to upsert with a non-existent `source_word_id` should raise `DatabaseError` (FK violation).

   Access the `asyncpg.Connection` through `neon_backend._connect()` (same pattern as existing integration tests via `# noqa: SLF001`).

3. **Run `make check`** in `packages/database/` and verify green.

## Production safety constraints (mandatory)

- **Database operations**: All integration tests run against the testing Neon database only (via `DATABASE_URL` from Doppler).
- Tests use unique data per test (UUID-based word forms) to avoid collisions.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the exact `_neon_exercise.py` extraction pattern (standalone async functions taking `asyncpg.Connection`).
- **Correct file locations**: `_neon_detailed.py` in `backend/` directory alongside existing extracted modules.
- **No regressions**: No existing files are modified.

## Error handling + correctness rules (mandatory)

- All `asyncpg.PostgresError` exceptions are caught and re-raised as `DatabaseError` (consistent with all other backend operations).
- FK violations (non-existent source_word_id) naturally raise `asyncpg.PostgresError`, which becomes `DatabaseError`.
- No empty catch blocks. No silent error suppression.

## Zero legacy tolerance rule (mandatory)

- N/A -- this task creates new code only.

## Acceptance criteria (testable)

1. `from nl_processing.database.backend._neon_detailed import get_word_details, upsert_word_detail` succeeds.
2. Integration test: A detail row can be upserted and retrieved with correct field values.
3. Integration test: Upserting the same `(source_word_id, word_type)` overwrites the row.
4. Integration test: `get_word_details` with empty or non-existent IDs returns `[]`.
5. Integration test: FK violation raises `DatabaseError`.
6. `make check` passes in `packages/database/`.
7. All new files under 200 lines.

## Verification / quality gates

- [x] Integration tests added against real Neon
- [x] Linters/formatters pass (`make check`)
- [x] No new warnings introduced
- [x] All new files under 200 lines
- [x] Error paths tested (FK violation, empty inputs)

## Edge cases

- JSONB payload with nested objects and arrays must round-trip correctly.
- Very large JSON payloads (within PostgreSQL limits) should work.
- Concurrent upserts to the same `(source_word_id, word_type)` should not deadlock (ON CONFLICT handles this).
- `asyncpg` passes JSON strings to JSONB columns; verify the conversion works.

## Notes / risks

- **Risk**: `asyncpg` JSONB handling may require explicit `json.dumps()` before passing to the query.
  - **Mitigation**: The `payload` parameter is typed as `str` (pre-serialized JSON). The caller (store layer in T5) is responsible for `json.dumps()`.
- **Design note**: The functions take `src` and `tgt` strings (not a pre-computed table name) to construct the table name internally via the query templates. This matches the pattern in `_neon_exercise.py` which takes table name strings.
