---
Task ID: T4
Title: Implement `DetailedWordStore` + backend methods + SQL queries + `create_tables()` update in `database`
Sprint: 2026-03-13_extract-word-details
Module: database
Depends on: T1
Parallelizable: yes, with T2 and T3
---

## Goal / value

After this task, `database` exposes a fully functional `DetailedWordStore` with `get_details()` and `get_or_extract_details()` methods. The backend abstraction (`AbstractBackend` + `NeonBackend`) has new methods for detailed-word CRUD. SQL queries for the `word_details_<src>_<tgt>` table are implemented. `create_tables()` now also creates the detailed-word table. Unit, integration, and e2e tests verify the full contract. `make check` passes.

## Context (contract mapping)

- Database spec: `packages/database/docs/module-spec.md` — FR-11 (DetailedWordStore API), FR-12 (persistence with schema metadata), FR-13 (get-or-extract read-through), FR-14 (fail-fast on bad data), DEC-8 (pair-specific tables), DEC-9 (inject extractor), DEC-10 (missing source word fails)
- Existing code: `packages/database/src/nl_processing/database/` — `backend/abstract.py`, `backend/neon.py`, `backend/_queries.py`, `service.py`, `detailed_models.py`, `detailed_ports.py`, `detailed_exceptions.py`

## Preconditions

- T1 complete: `_schema_registry.py` and `_serializer.py` exist in `extract_word_details` (the schema registry contract is needed for payload validation logic)
- Existing database package is fully functional
- `detailed_models.py`, `detailed_ports.py`, `detailed_exceptions.py` already exist with scaffold types

## Non-goals

- Implementing the `WordDetailsExtractor` (T3 — that's the injected dependency)
- Cache layer (T5)
- Root config updates (T6)
- Modifying existing `DatabaseService` or `ExerciseProgressStore` behavior

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `packages/database/src/nl_processing/database/` — source code
- `packages/database/tests/` — tests
- `packages/database/pyproject.toml` — if a new dependency is needed
- `packages/database/Makefile` — if PYTHONPATH needs updating

**FORBIDDEN — this task must NEVER touch:**

- `packages/extract_word_details/` (T1/T2/T3 own that)
- `packages/database_cache/` (T5 owns that)
- `packages/core/`
- Root configs

**Test scope:**

- Tests go in: `packages/database/tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- Test command: `make check` in `packages/database/`

## Touched surface (expected files / modules)

**New files to create:**

- `src/nl_processing/database/detailed_store.py` — `DetailedWordStore` class
- `src/nl_processing/database/backend/_neon_detailed.py` — NeonBackend helper functions for detailed-word SQL operations
- `src/nl_processing/database/backend/_queries_detailed.py` — SQL query templates for detailed-word table
- `tests/unit/database/test_detailed_store.py` — unit tests with mock backend
- `tests/integration/database/test_detailed_store_integration.py` — integration tests with real Neon DB
- `tests/e2e/database/test_detailed_e2e.py` — e2e tests for get-or-extract flow

**Files to modify:**

- `src/nl_processing/database/backend/abstract.py` — add abstract methods for detailed-word CRUD
- `src/nl_processing/database/backend/neon.py` — implement new abstract methods using helpers from `_neon_detailed.py`
- `src/nl_processing/database/backend/_queries.py` — add `create_word_details_table()` function (or put in `_queries_detailed.py`)
- `tests/unit/database/mock_backend.py` — add mock implementations of new backend methods
- `packages/database/pyproject.toml` — add `nl-processing-extract-word-details` as dev dependency (for integration/e2e tests that need the extractor)
- `packages/database/Makefile` — add `../extract_word_details/src` to `PACKAGE_PYTHONPATH`

## Dependencies and sequencing notes

- Depends on T1 for schema registry contract (schema_key, schema_version concepts)
- Does NOT depend on T2 or T3 — the `DetailedWordStore` works through the injected `DetailedWordExtractorPort` protocol. Unit tests mock the extractor.
- T5 depends on this task for the remote store contract.
- Integration/e2e tests need a working extractor to test `get_or_extract_details()`. Options:
  (a) Use a mock extractor in integration tests (preferred for independence)
  (b) Use the real extractor from T3 in e2e tests (requires T3 to be complete)
  **Decision**: Unit and integration tests use a mock extractor. E2e tests can also use a mock extractor or test only `get_details()` (read-only path). If the dev wants to test the full flow with a real extractor, they should wait for T3. The task is still independently completable with mocks.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncpg` v0.30 (already in repo)
  - **Relevant docs**: https://magicstack.github.io/asyncpg/current/
  - **API**: `connection.execute(query, *args)`, `connection.fetch(query, *args)`, `connection.fetchrow(query, *args)`
  - **Usage**: Same pattern as existing `_neon_words.py` and `_neon_exercise.py`
  - **Gotcha**: `asyncpg` uses `$1, $2, ...` parameter placeholders (not `?` like SQLite)

- **Schema registry interaction**: The `DetailedWordStore` must validate payloads. Two approaches:
  1. Import the schema registry from `extract_word_details` — but that creates a runtime dependency
  2. Validate using Pydantic `model_validate()` on `DetailedWordRecord` only (which the database already owns)

  **Decision**: The `DetailedWordStore` validates that stored rows have valid `schema_key` and `schema_version`, and that the `payload` is a valid JSON dict. Deep payload validation (against POS-specific models) is the responsibility of the extractor. The store trusts the extractor to return validated `DetailedWordRecord` instances. On reads, the store returns raw `DetailedWordRecord` objects. Downstream consumers (like `database_cache`) that want to parse into typed POS models use the schema registry themselves.

  This keeps `database` independent of `extract_word_details` at runtime — only dev-dependency for tests.

## Implementation steps (developer-facing)

1. **Add new abstract methods to `AbstractBackend` (`abstract.py`)**:
   ```python
   @abstractmethod
   async def upsert_word_details(
       self, table: str, source_word_id: int, word_type: str,
       schema_key: str, schema_version: int, payload: str,
   ) -> None:
       """Insert or update a detailed-word row. Keyed by (source_word_id, word_type)."""

   @abstractmethod
   async def get_word_details(
       self, table: str, source_word_id: int, word_type: str,
   ) -> dict[str, str | int] | None:
       """Return the detailed-word row or None."""

   @abstractmethod
   async def get_word_details_batch(
       self, table: str, source_word_ids_and_types: list[tuple[int, str]],
   ) -> list[dict[str, str | int]]:
       """Return detailed-word rows for a batch of (source_word_id, word_type) pairs."""
   ```

2. **Create `_queries_detailed.py`** — SQL query templates:
   ```python
   def create_word_details_table(src: str, tgt: str) -> str:
       return f"""
           CREATE TABLE IF NOT EXISTS word_details_{src}_{tgt} (
               id SERIAL PRIMARY KEY,
               source_word_id INTEGER NOT NULL REFERENCES words_{src}(id),
               word_type VARCHAR NOT NULL,
               schema_key VARCHAR NOT NULL,
               schema_version INTEGER NOT NULL,
               payload JSONB NOT NULL,
               created_at TIMESTAMP NOT NULL DEFAULT NOW(),
               updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
               UNIQUE(source_word_id, word_type)
           )
       """

   def upsert_word_details_query(table: str) -> str:
       return f"""
           INSERT INTO word_details_{table} (source_word_id, word_type, schema_key, schema_version, payload, updated_at)
           VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
           ON CONFLICT (source_word_id, word_type)
           DO UPDATE SET schema_key = $3, schema_version = $4, payload = $5::jsonb, updated_at = NOW()
       """

   def get_word_details_query(table: str) -> str:
       return f"""
           SELECT source_word_id, word_type, schema_key, schema_version, payload
           FROM word_details_{table}
           WHERE source_word_id = $1 AND word_type = $2
       """

   def get_word_details_batch_query(table: str, count: int) -> str:
       # Build WHERE clause for batch: (source_word_id, word_type) IN (($1,$2), ($3,$4), ...)
       # OR use individual queries in a loop (simpler, still efficient for small batches)
       ...
   ```

3. **Create `_neon_detailed.py`** — NeonBackend helper functions:
   - `upsert_details(conn, table, source_word_id, word_type, schema_key, schema_version, payload)` — execute upsert query
   - `get_details(conn, table, source_word_id, word_type)` — fetch single row
   - `get_details_batch(conn, table, source_word_ids_and_types)` — fetch batch

4. **Implement concrete methods in `NeonBackend` (`neon.py`)**:
   - `upsert_word_details()` — delegate to `_neon_detailed.upsert_details()`
   - `get_word_details()` — delegate to `_neon_detailed.get_details()`
   - `get_word_details_batch()` — delegate to `_neon_detailed.get_details_batch()`

5. **Update `NeonBackend.create_tables()`** to also create the detailed-word table:
   - After creating translation tables, also execute `create_word_details_table(src, tgt)` for each pair
   - Import `create_word_details_table` from `_queries_detailed.py`

6. **Implement `detailed_store.py` — `DetailedWordStore`**:

   Constructor:
   - Parameters: `source_language: Language`, `target_language: Language`, `backend: AbstractBackend | None = None`, `extractor: DetailedWordExtractorPort | None = None`
   - If `backend is None`, create `NeonBackend` from `read_database_url()` (same pattern as `DatabaseService`)
   - Store pair info for table naming: `self._details_table = f"{src}_{tgt}"`

   `get_details(words: list[Word]) -> list[DetailedWordRecord]`:
   - For each word, look up the canonical source_word_id via `backend.get_word(source_table, word.normalized_form)`
   - If source word not found, raise `SourceWordNotFoundError` (FR-14, DEC-10)
   - Fetch detailed-word row via `backend.get_word_details(details_table, source_word_id, word.word_type.value)`
   - For found rows, construct `DetailedWordRecord` from the stored data (parse payload JSON back into dict)
   - Return results for found rows only (in input order, skipping words without details)

   `get_or_extract_details(words: list[Word]) -> list[DetailedWordRecord]`:
   - If no extractor injected, raise `ValueError`
   - Read persisted details first (using `get_details` logic)
   - Identify misses (words without persisted details)
   - If no misses, return all from storage
   - Call `extractor.extract(misses)` to get new records
   - Persist each new record via `backend.upsert_word_details()`
   - Merge and return in supported-input order (FR-13)

7. **Update `MockBackend` (`mock_backend.py`)** — add in-memory implementations of the three new abstract methods.

8. **Write unit tests (`test_detailed_store.py`)**:
   - Test `get_details()` with word in corpus + detail exists → returns record
   - Test `get_details()` with word NOT in corpus → raises `SourceWordNotFoundError`
   - Test `get_details()` with word in corpus but no detail → returns empty list
   - Test `get_or_extract_details()` all hits → no extractor call
   - Test `get_or_extract_details()` all misses → extractor called with misses, results persisted
   - Test `get_or_extract_details()` mixed hits/misses → extractor called only for misses
   - Test `get_or_extract_details()` with no extractor → raises `ValueError`
   - Use `MockBackend` from existing test infrastructure

9. **Write integration tests (`test_detailed_store_integration.py`)**:
   - Use real Neon DB (under `doppler run --`)
   - Create tables, insert a source word, persist a detailed record, read it back
   - Verify round-trip: persisted payload matches original
   - Verify `create_tables()` creates the `word_details_nl_ru` table
   - Use a mock extractor for `get_or_extract_details()` integration test

10. **Write e2e tests (`test_detailed_e2e.py`)**:
    - Full flow: create tables → add source word → `get_or_extract_details()` with mock extractor → verify persisted → call again → verify no re-extraction
    - Verify `get_details()` returns the persisted record

11. **Verify**: Run `make check` in `packages/database/`. All tests pass (existing + new).

## Production safety constraints (mandatory)

- **Database operations**: All integration/e2e tests target the TESTING database via `doppler run --`. The `create_tables()` extension uses `CREATE TABLE IF NOT EXISTS` — idempotent and safe.
- **The new `word_details_nl_ru` table does NOT exist in production yet.** The first `create_tables()` call in production will create it. This is safe because it's additive only (no schema changes to existing tables).

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extend existing `AbstractBackend`/`NeonBackend` pattern. Reuse `_database_config.read_database_url()`. Reuse existing query template patterns from `_queries.py`.
- **Correct libraries only**: `asyncpg>=0.30,<1` — already in database package.
- **Correct file locations**: New backend files under `backend/`. New store file at module root. Queries in `_queries_detailed.py`.
- **No regressions**: Existing tests must continue passing. `MockBackend` must be updated to include new abstract methods.

## Error handling + correctness rules (mandatory)

- `SourceWordNotFoundError` when source word is not in the corpus (DEC-10, FM-6)
- `PayloadValidationError` if a persisted payload fails to parse (FM-7) — though the store trusts the extractor to return valid records, the read path should handle corrupt stored data gracefully by raising, not silently dropping
- `SchemaVersionError` if a persisted row has an unknown schema version — not implemented at the store level in V1 (the store stores and returns raw records; version checking is a consumer concern). But the store MUST validate that `schema_key` and `schema_version` fields are present and non-empty before persisting.
- `ValueError` if `get_or_extract_details()` is called without an injected extractor

## Zero legacy tolerance rule (mandatory)

- The new `DetailedWordStore` is additive — no existing code paths are superseded.
- The `MockBackend` update must not break existing unit tests.

## Acceptance criteria (testable)

1. `AbstractBackend` has three new abstract methods: `upsert_word_details`, `get_word_details`, `get_word_details_batch`.
2. `NeonBackend` implements all three with correct SQL.
3. `NeonBackend.create_tables()` now creates `word_details_<src>_<tgt>` table for each configured pair.
4. `DetailedWordStore.get_details()` returns persisted records for known words and raises `SourceWordNotFoundError` for unknown words.
5. `DetailedWordStore.get_or_extract_details()` reads first, extracts misses, persists, and returns merged.
6. `DetailedWordStore.get_or_extract_details()` without extractor raises `ValueError`.
7. `MockBackend` implements all new abstract methods.
8. All existing `database` tests still pass.
9. `make check` passes in `packages/database/`.
10. No file exceeds 200 lines.

## Verification / quality gates

- [x] Unit tests added (DetailedWordStore with mock backend, all paths)
- [x] Integration tests added (real Neon DB CRUD for detailed words)
- [x] E2E tests added (full get-or-extract flow)
- [x] Existing tests unbroken
- [x] Linters/formatters pass
- [x] No new warnings
- [x] Negative-path tests (missing source word, no extractor, corrupt data)
- [x] No file exceeds 200 lines

## Edge cases

- `get_details([])` — empty input should return `[]`
- `get_or_extract_details([])` — return `[]`, no extractor call
- Source word exists but has no translation yet — `get_details` should still work (detailed records are keyed by source_word_id, not by translation)
- Two words with same `normalized_form` but different `word_type` — both should get separate detailed rows (UNIQUE on `source_word_id, word_type`)
- `upsert_word_details` for an existing (source_word_id, word_type) pair — should UPDATE, not INSERT duplicate
- Payload is stored as JSONB — verify round-trip preserves all nested fields

## Notes / risks

- **Backend method naming**: The `table` parameter in backend methods uses the pair suffix (e.g., `"nl_ru"`), not the full table name. The SQL query templates prepend `word_details_`.
- **Payload serialization**: The `payload` field in `DetailedWordRecord` is `dict[str, Any]`. When storing in JSONB, use `json.dumps()` to convert. When reading back, `asyncpg` returns JSONB as a Python dict automatically.
- **File size**: `abstract.py` is currently 170 lines. Adding 3 new methods (~15 lines) pushes it close to 200. If it exceeds, extract the detailed-word methods into a separate mixin or extend the base class differently. The dev should monitor this.
