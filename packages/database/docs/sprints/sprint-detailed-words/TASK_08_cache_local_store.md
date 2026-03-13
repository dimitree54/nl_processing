---
Task ID: `T8`
Title: `Define cache-side port, local SQLite store, and queries for detailed-word caching`
Sprint: `2026-03-13_detailed-words`
Module: `database_cache`
Depends on: `T1`
Parallelizable: `yes, with T2-T4`
---

## Goal / value

Build the local storage foundation for the detailed-word cache in the `database_cache` package. After this task, pair-scoped local SQLite tables, DDL, CRUD queries, and the `RemoteDetailedWordPort` protocol exist, ready for the cache service (T9).

## Context (contract mapping)

- Requirements: `packages/database_cache/docs/module-spec.md` -- FR-12 (dedicated pair-scoped local SQLite), FR-14 (schema version round-trip), DEC-7 (pair-scoped separate from practice), DEC-9 (invalidate incompatible versions)
- Pattern reference: `packages/database_cache/src/nl_processing/database_cache/_local_store_queries.py` (existing query constants)
- Pattern reference: `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py` (existing base class)
- Pattern reference: `packages/database_cache/src/nl_processing/database_cache/ports.py` (existing port protocol)

## Preconditions

- T1 completed: `DetailedWordRecord` model exists in `database` package (imported by cache).

## Non-goals

- No cache service implementation (that's T9).
- No modification to existing `local_store.py`, `_local_store_queries.py`, `_local_store_base.py`, or `ports.py`.
- No modification to existing `DatabaseCacheService`.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `packages/database_cache/src/nl_processing/database_cache/` -- new files only
- `packages/database_cache/tests/unit/database_cache/` -- new test files only

**FORBIDDEN -- this task must NEVER touch:**
- `packages/database_cache/src/nl_processing/database_cache/local_store.py` (existing)
- `packages/database_cache/src/nl_processing/database_cache/_local_store_queries.py` (existing)
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py` (existing)
- `packages/database_cache/src/nl_processing/database_cache/ports.py` (existing)
- `packages/database_cache/src/nl_processing/database_cache/service.py` (existing)
- `src/nl_processing/core/` or any core package file
- `packages/database/` source code (read-only import of `DetailedWordRecord`)

**Test scope:**
- Tests go in: `tests/unit/database_cache/`
- Test command: `make check` (in `packages/database_cache/`)
- Working directory: `packages/database_cache/`

## Touched surface (expected files / modules)

**New files to create:**
- `src/nl_processing/database_cache/_detailed_queries.py` (~40-60 lines) -- DDL and SQL for local detailed-word cache
- `src/nl_processing/database_cache/detailed_local_store.py` (~80-120 lines) -- Local SQLite store for detailed-word cache
- `src/nl_processing/database_cache/detailed_ports.py` (~20-30 lines) -- `RemoteDetailedWordPort` protocol
- `tests/unit/database_cache/test_detailed_local_store.py` (~80-120 lines) -- Unit tests

## Dependencies and sequencing notes

- Depends on T1 for `DetailedWordRecord` model (imported from `nl_processing.database.detailed_models`).
- T9 depends on this for the local store and port protocol.
- Can run in parallel with T2-T4 (database backend work).

## Third-party / library research (mandatory for any external dependency)

- **Library**: `aiosqlite` -- already used in `database_cache`. Same version.
  - `await conn.execute(sql, params)` for DML
  - `await cur.fetchall()` returns list of `Row` objects
  - `Row` can be converted to `dict(row)`
- **Library**: `json` -- standard library, for payload serialization.
- No new dependencies.

## Implementation steps (developer-facing)

1. **Create `src/nl_processing/database_cache/_detailed_queries.py`:**

   ```python
   """DDL and query constants for the local detailed-word cache store."""

   DDL_CACHED_WORD_DETAILS = """
   CREATE TABLE IF NOT EXISTS cached_word_details (
       source_word TEXT NOT NULL,
       word_type TEXT NOT NULL,
       schema_key TEXT NOT NULL,
       schema_version INTEGER NOT NULL,
       payload TEXT NOT NULL,
       cached_at TEXT NOT NULL,
       PRIMARY KEY (source_word, word_type)
   )"""

   DETAILED_DDL = [DDL_CACHED_WORD_DETAILS]

   INSERT_DETAIL = (
       "INSERT OR REPLACE INTO cached_word_details "
       "(source_word, word_type, schema_key, schema_version, payload, cached_at) "
       "VALUES (?, ?, ?, ?, ?, ?)"
   )

   SELECT_DETAILS = (
       "SELECT source_word, word_type, schema_key, schema_version, payload "
       "FROM cached_word_details "
       "WHERE source_word = ? AND word_type = ?"
   )

   DELETE_INCOMPATIBLE = (
       "DELETE FROM cached_word_details "
       "WHERE source_word = ? AND word_type = ? AND schema_version != ?"
   )
   ```

   Note: The local table uses `(source_word, word_type)` as PK since the cache doesn't have `source_word_id` (that's a remote DB concept). It uses the `normalized_form` string directly.

2. **Create `src/nl_processing/database_cache/detailed_ports.py`:**

   ```python
   """Port protocol for remote detailed-word operations."""
   from typing import Protocol, runtime_checkable
   from nl_processing.core.models import Word
   from nl_processing.database.detailed_models import DetailedWordRecord

   @runtime_checkable
   class RemoteDetailedWordPort(Protocol):
       """Remote contract for fetching detailed-word records."""
       async def get_or_extract_details(
           self, words: list[Word],
       ) -> list[DetailedWordRecord]: ...
   ```

   This protocol matches the `DetailedWordStore.get_or_extract_details()` signature so the real store can be injected directly.

3. **Create `src/nl_processing/database_cache/detailed_local_store.py`:**

   A new `DetailedWordLocalStore` class (separate from `LocalStore`) using `_local_store_base.py` patterns but with its own SQLite file:

   ```python
   class DetailedWordLocalStore:
       def __init__(self, db_path: str) -> None: ...

       async def open(self) -> None:
           """Open SQLite connection and create tables."""

       async def close(self) -> None:
           """Close SQLite connection."""

       async def get_cached_details(
           self, words: list[tuple[str, str]],
       ) -> list[dict[str, str | int]]:
           """Fetch cached detail rows for (source_word, word_type) pairs."""

       async def upsert_detail(
           self, source_word: str, word_type: str,
           schema_key: str, schema_version: int, payload: str,
       ) -> None:
           """Insert or replace a cached detail row."""

       async def invalidate_incompatible(
           self, source_word: str, word_type: str, expected_version: int,
       ) -> None:
           """Delete cached rows whose schema_version doesn't match."""
   ```

   The class manages its own `aiosqlite.Connection` (same pattern as `LocalStoreBase`).

4. **Create `tests/unit/database_cache/test_detailed_local_store.py`:**

   Tests using a temporary SQLite file (`:memory:` or `tmp_path`):

   - **Test open creates tables**: After `open()`, the `cached_word_details` table exists.
   - **Test upsert and get**: Upsert a detail row, then retrieve it. Verify fields match.
   - **Test upsert overwrites**: Upsert same `(source_word, word_type)` twice with different payload. Verify latest is returned.
   - **Test get_cached_details miss**: Query for non-existent word returns empty list.
   - **Test get_cached_details multiple**: Upsert two different words, query both, verify both returned.
   - **Test invalidate_incompatible**: Upsert a row with version 1, call invalidate with expected version 2. Verify row is deleted. Upsert version 2, call invalidate with version 2, verify row is kept.
   - **Test `RemoteDetailedWordPort` is runtime checkable**: An object with the correct method is recognized by `isinstance`.

5. **Run `make check`** in `packages/database_cache/` and verify green.

## Production safety constraints (mandatory)

- **Database operations**: Only local SQLite operations in tests. No remote database access.
- **File isolation**: Tests use temporary SQLite files that don't collide with production.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the `_local_store_base.py` pattern for SQLite operations. Follow the `ports.py` pattern for protocol definitions.
- **Correct file locations**: New files in `src/nl_processing/database_cache/` and `tests/unit/database_cache/`.
- **No regressions**: No existing files modified.

## Error handling + correctness rules (mandatory)

- All `sqlite3.Error` exceptions caught and re-raised as `CacheStorageError` (consistent with existing local store).
- No empty catch blocks. No silent error suppression.

## Zero legacy tolerance rule (mandatory)

- N/A -- this task creates new code only.

## Acceptance criteria (testable)

1. `from nl_processing.database_cache.detailed_local_store import DetailedWordLocalStore` succeeds.
2. `from nl_processing.database_cache.detailed_ports import RemoteDetailedWordPort` succeeds.
3. `DetailedWordLocalStore` can open, upsert, query, and invalidate detailed-word cache rows.
4. `RemoteDetailedWordPort` is `@runtime_checkable` and matches `DetailedWordStore.get_or_extract_details()` signature.
5. All unit tests pass.
6. `make check` passes in `packages/database_cache/`.
7. All new files under 200 lines.

## Verification / quality gates

- [x] Unit tests added for local store CRUD and invalidation
- [x] Linters/formatters pass (`make check`)
- [x] No new warnings introduced
- [x] All new files under 200 lines
- [x] Protocol runtime-checkable test

## Edge cases

- SQLite file doesn't exist yet: `open()` creates it.
- Schema version changes between extractor versions: `invalidate_incompatible()` deletes stale rows.
- `payload` is stored as TEXT (JSON string) in SQLite, not as a native JSON type.
- Empty word list: `get_cached_details([])` returns `[]`.

## Notes / risks

- **Design decision**: The local cache uses `(source_word, word_type)` as the key, not `source_word_id`. This is because the cache doesn't track remote IDs for detailed words (unlike the practice cache which tracks word pair IDs). The string-based key is simpler and doesn't require a word ID lookup.
- **Design decision**: `DetailedWordLocalStore` is completely separate from `LocalStore` (the practice cache store). They use different SQLite files, different tables, and different lifecycles. This matches DEC-7 (pair-scoped separate from practice).
- **Risk**: Importing `DetailedWordRecord` from the `database` package creates a cross-package dependency.
  - **Mitigation**: This is expected and acceptable -- `database_cache` already depends on `database` (see `pyproject.toml`). The `RemoteDetailedWordPort` protocol also references `DetailedWordRecord`.
