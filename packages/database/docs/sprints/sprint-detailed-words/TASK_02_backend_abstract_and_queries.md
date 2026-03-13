---
Task ID: `T2`
Title: `Add abstract backend methods, DDL, and SQL queries for detailed-word table`
Sprint: `2026-03-13_detailed-words`
Module: `database`
Depends on: `T1`
Parallelizable: `no`
---

## Goal / value

Define the backend contract (abstract methods) and SQL templates for the `word_details_<src>_<tgt>` table. After this task, the DDL for table creation, the CRUD SQL queries, and the abstract method signatures exist, ready for Neon implementation.

## Context (contract mapping)

- Requirements: `packages/database/docs/module-spec.md` -- FR-12 (pair-specific table, schema_key, schema_version, payload columns), FR-5 (create_tables DDL), DEC-8 (pair-specific tables with versioned JSON)
- Pattern reference: `src/nl_processing/database/backend/_queries.py` (DDL functions), `_queries_delete.py` (split query pattern)
- Pattern reference: `src/nl_processing/database/backend/abstract.py` (existing ABC)

## Preconditions

- T1 completed: `DetailedWordRecord`, `DetailedWordExtractorPort`, and detailed exceptions exist.

## Non-goals

- No Neon implementation (that's T4).
- No modification to existing `abstract.py` (170 lines, must not grow).
- No modification to existing `_queries.py` (188 lines, must not grow).
- No `create_tables()` wiring (that's T3).
- No store logic.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `src/nl_processing/database/backend/` -- new files only
- `tests/unit/database/` -- new test files only

**FORBIDDEN -- this task must NEVER touch:**
- `src/nl_processing/database/backend/abstract.py` (existing, 170 lines)
- `src/nl_processing/database/backend/_queries.py` (existing, 188 lines)
- Any existing file
- `src/nl_processing/core/` or any core package file

**Test scope:**
- Tests go in: `tests/unit/database/`
- Test command: `make check` (in `packages/database/`)

## Touched surface (expected files / modules)

**New files to create:**
- `src/nl_processing/database/backend/_abstract_detailed.py` (~50-70 lines) -- Abstract mixin/ABC for detailed-word backend methods
- `src/nl_processing/database/backend/_queries_detailed.py` (~80-120 lines) -- DDL and SQL query templates
- `tests/unit/database/test_queries_detailed.py` (~50-70 lines) -- Query template tests

## Dependencies and sequencing notes

- Depends on T1 for the `DetailedWordRecord` model (used in docstrings and type context).
- T3 depends on this task for DDL functions and abstract method signatures.
- T4 depends on this task for SQL query templates and abstract methods.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncpg` -- already used. No new version needed.
- **Library**: `abc.ABC` / `abc.abstractmethod` -- standard library, already used.
- No new third-party dependencies.

## Implementation steps (developer-facing)

1. **Create `src/nl_processing/database/backend/_queries_detailed.py`:**

   Define SQL template functions (following the pattern in `_queries.py` and `_queries_delete.py`):

   - `create_word_details_table(src: str, tgt: str) -> str`: DDL for `word_details_<src>_<tgt>` table with columns:
     - `id SERIAL PRIMARY KEY`
     - `source_word_id INTEGER NOT NULL REFERENCES words_<src>(id)` -- FK to canonical word
     - `word_type VARCHAR NOT NULL` -- the POS value string
     - `schema_key VARCHAR NOT NULL` -- e.g., "nl_ru_noun"
     - `schema_version INTEGER NOT NULL` -- version integer
     - `payload JSONB NOT NULL` -- the detailed data
     - `created_at TIMESTAMP NOT NULL DEFAULT NOW()`
     - `updated_at TIMESTAMP NOT NULL DEFAULT NOW()`
     - `UNIQUE(source_word_id, word_type)` -- one detail row per (word, type) pair
   - `get_word_details_query(src: str, tgt: str) -> str`: SELECT rows by source_word_ids list
   - `upsert_word_detail_query(src: str, tgt: str) -> str`: INSERT ... ON CONFLICT(source_word_id, word_type) DO UPDATE for schema_key, schema_version, payload, updated_at
   - All functions must use `# noqa: S608` on f-string SQL lines (same pattern as existing queries).

2. **Create `src/nl_processing/database/backend/_abstract_detailed.py`:**

   Define an abstract class `AbstractDetailedWordBackend(ABC)` as a **separate ABC** (not modifying existing `AbstractBackend`):

   - `async def get_word_details(self, table: str, source_word_ids: list[int]) -> list[dict[str, str | int]]` -- return detail rows
   - `async def upsert_word_detail(self, table: str, source_word_id: int, word_type: str, schema_key: str, schema_version: int, payload: str) -> None` -- upsert one detail row (payload as JSON string)
   - `async def create_word_details_table(self, src: str, tgt: str) -> None` -- create the detailed-word table

   Import `ABC, abstractmethod` from `abc`.

3. **Create `tests/unit/database/test_queries_detailed.py`:**
   - Test that `create_word_details_table("nl", "ru")` returns SQL containing `word_details_nl_ru`, `SERIAL PRIMARY KEY`, `source_word_id`, `JSONB`, `UNIQUE`.
   - Test that `get_word_details_query("nl", "ru")` returns SQL containing `SELECT` and `word_details_nl_ru`.
   - Test that `upsert_word_detail_query("nl", "ru")` returns SQL containing `INSERT INTO word_details_nl_ru` and `ON CONFLICT`.
   - These are string-content tests, not execution tests (same pattern as testing query templates).

4. **Run `make check`** in `packages/database/` and verify green.

## Production safety constraints (mandatory)

- **Database operations**: No database operations in this task. Only SQL template functions and abstract class definitions.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the exact same SQL template function pattern from `_queries.py` and `_queries_delete.py`. Follow the ABC pattern from `abstract.py`.
- **Correct file locations**: New files in `src/nl_processing/database/backend/` with `_` prefix (internal modules) following existing convention.
- **No regressions**: No existing files are modified.

## Error handling + correctness rules (mandatory)

- Abstract methods document their error contract in docstrings.
- SQL templates must use parameterized queries ($1, $2, etc.) for data values; only table names are f-string formatted.

## Zero legacy tolerance rule (mandatory)

- N/A -- this task creates new code only.

## Acceptance criteria (testable)

1. `from nl_processing.database.backend._queries_detailed import create_word_details_table, get_word_details_query, upsert_word_detail_query` succeeds.
2. `create_word_details_table("nl", "ru")` returns valid DDL with `word_details_nl_ru`, FK reference to `words_nl`, JSONB payload, and UNIQUE constraint.
3. `from nl_processing.database.backend._abstract_detailed import AbstractDetailedWordBackend` succeeds.
4. `AbstractDetailedWordBackend` has three abstract methods: `get_word_details`, `upsert_word_detail`, `create_word_details_table`.
5. Query template tests pass.
6. `make check` passes in `packages/database/`.
7. All new files are under 200 lines.

## Verification / quality gates

- [x] Unit tests added for SQL templates
- [x] Linters/formatters pass (`make check`)
- [x] No new warnings introduced
- [x] All new files under 200 lines

## Edge cases

- Table names with different language pairs (e.g., `word_details_nl_en`) should work correctly.
- The UNIQUE constraint on `(source_word_id, word_type)` means one detail row per word+POS combination per pair table.

## Notes / risks

- **Risk**: The abstract class is a separate ABC, not extending `AbstractBackend`. This means the Neon implementation needs to implement both.
  - **Mitigation**: T4 creates `_neon_detailed.py` as standalone functions (same pattern as `_neon_exercise.py`), and a thin `NeonDetailedWordBackend` class that delegates to them. The main `NeonBackend` is not modified.
- **Design note**: The `payload` column is `JSONB` (not `JSON`) to enable future PostgreSQL JSON operators if needed.
- **Design note**: The `upsert` query uses `ON CONFLICT(source_word_id, word_type) DO UPDATE` to overwrite existing detail data when re-extracting.
