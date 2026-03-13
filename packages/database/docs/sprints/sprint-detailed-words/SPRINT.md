---
Sprint ID: `2026-03-13_detailed-words`
Sprint Goal: `Deliver DetailedWordStore in database and DetailedWordCacheService in database_cache (FR-11 through FR-14 in both modules)`
Sprint Type: `module`
Module: `database` + `database_cache`
Status: `planning`
Owners: `Developer`
---

## Goal

Implement purely additive `DetailedWordStore` in the `database` package and `DetailedWordCacheService` in the `database_cache` package. This covers FR-11 through FR-14 in the database module spec and FR-11 through FR-15 in the database_cache module spec. No existing code behavior is changed.

## Module Scope

### What this sprint implements
- Module: `database` (tasks T1-T7) and `database_cache` (tasks T8-T9)
- Database module spec: `packages/database/docs/module-spec.md` (FR-11 through FR-14, FR-5 update, DEC-8 through DEC-11, BR-8, BR-9)
- Database cache module spec: `packages/database_cache/docs/module-spec.md` (FR-11 through FR-15, DEC-7 through DEC-9)

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED -- this sprint may ONLY touch:**
- `packages/database/src/nl_processing/database/` -- database module source code (NEW files only, except T3 minimal additions to `_queries.py` and `neon.py`)
- `packages/database/tests/` -- database module tests
- `packages/database_cache/src/nl_processing/database_cache/` -- cache module source code (NEW files only)
- `packages/database_cache/tests/` -- cache module tests
- `docs/sprints/sprint-detailed-words/` -- this sprint's planning files

**FORBIDDEN -- this sprint must NEVER touch:**
- `src/nl_processing/core/` or any `core` package file
- Existing `DatabaseService`, `ExerciseProgressStore`, `CacheSyncer`, `DatabaseCacheService` class behavior
- Existing test files (do not modify, only add new test files)
- Bot code, configs, or infrastructure outside these two modules
- `packages/extract_word_details/` (read-only reference for protocol design)

### Test Scope
- **Database test directories**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- **Database test command**: `make check` (in `packages/database/`)
- **Cache test directories**: `tests/unit/database_cache/`, `tests/integration/database_cache/`
- **Cache test command**: `make check` (in `packages/database_cache/`)
- **NEVER run**: Tests from other packages

## Interface Contract

### Public interface this sprint implements

**New `DetailedWordStore` (database package):**
```python
class DetailedWordStore:
    def __init__(
        self,
        source_language: Language,
        target_language: Language,
        backend: AbstractDetailedWordBackend | None = None,
        extractor: DetailedWordExtractorPort | None = None,
    ) -> None: ...

    async def get_details(
        self,
        words: list[Word],
    ) -> list[DetailedWordRecord]: ...

    async def get_or_extract_details(
        self,
        words: list[Word],
    ) -> list[DetailedWordRecord]: ...
```

**New `DetailedWordCacheService` (database_cache package):**
```python
class DetailedWordCacheService:
    def __init__(
        self,
        source_language: Language,
        target_language: Language,
        remote_store: RemoteDetailedWordPort | None = None,
        local_store: DetailedWordLocalStore | None = None,
        cache_dir: str | None = None,
    ) -> None: ...

    async def get_or_fetch_details(
        self,
        words: list[Word],
    ) -> list[DetailedWordRecord]: ...
```

### New types (database package):
```python
class DetailedWordRecord(BaseModel):
    source_word: str
    word_type: str
    schema_key: str
    schema_version: int
    payload: dict[str, Any]

class DetailedWordExtractorPort(Protocol):
    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]: ...
```

## Scope

### In
- FR-11 through FR-14 (database): `DetailedWordStore` with get/get-or-extract, backend methods, DDL, protocol types, models, and tests
- FR-5 update (database): `create_tables()` creates `word_details_<src>_<tgt>` table
- FR-11 through FR-15 (database_cache): `DetailedWordCacheService` with pair-scoped SQLite, read-through caching, schema version invalidation, and tests
- Protocol types for extractor dependency (`DetailedWordExtractorPort`)
- New backend abstract methods and Neon implementation for detailed-word CRUD
- Unit tests (mock backend), integration tests (real Neon), e2e tests

### Out
- Changes to existing `DatabaseService`, `ExerciseProgressStore`, `DatabaseCacheService` behavior
- Changes to `core` package
- Implementation of `extract_word_details` package
- Migration tooling or admin UIs
- Actual LLM extraction logic

## Inputs (contracts)

- Database module spec: `packages/database/docs/module-spec.md` -- FR-11 through FR-14, FR-5, DEC-8 through DEC-11, BR-8, BR-9
- Cache module spec: `packages/database_cache/docs/module-spec.md` -- FR-11 through FR-15, DEC-7 through DEC-9
- Extractor module spec: `packages/extract_word_details/docs/module-spec.md` -- FR-9 (schema registry), IF-4, DEC-5
- Core models: `packages/core/src/nl_processing/core/models.py` (read-only)

## Change digest

- **Requirement deltas**:
  - FR-11 (database): New `DetailedWordStore` class with `get_details()` and `get_or_extract_details()`
  - FR-12 (database): Pair-specific `word_details_<src>_<tgt>` table with schema metadata and JSON payload
  - FR-13 (database): Read-through extraction for cache misses via injected extractor
  - FR-14 (database): Fail-fast for missing words, unsupported schemas, invalid payloads
  - FR-5 (database): `create_tables()` must also create detailed-word table
  - FR-11 (cache): New `DetailedWordCacheService` class
  - FR-12 (cache): Pair-scoped local SQLite separate from practice cache
  - FR-13 (cache): `get_or_fetch_details()` with read-through
  - FR-14 (cache): Schema version invalidation on incompatible local rows
  - FR-15 (cache): Remote fetch failures leave local cache unchanged

## Task list (dependency-aware)

### database package (working directory: `packages/database/`)

- **T1:** `TASK_01_models_and_protocols.md` (depends: --) -- Define DetailedWordRecord model, DetailedWordExtractorPort protocol, and new exceptions
- **T2:** `TASK_02_backend_abstract_and_queries.md` (depends: T1) -- Add abstract backend methods, DDL, and SQL queries for detailed-word table in new files
- **T3:** `TASK_03_create_tables_integration.md` (depends: T2) -- Wire detailed-word DDL into `create_tables()` flow (minimal edits to existing files + decomposition)
- **T4:** `TASK_04_neon_detailed_words.md` (depends: T3) -- Implement Neon backend methods for detailed-word CRUD with integration tests
- **T5:** `TASK_05_detailed_word_store.md` (depends: T4) -- Implement `DetailedWordStore` public API with unit tests
- **T6:** `TASK_06_database_e2e_tests.md` (depends: T5) -- Add e2e tests for full DetailedWordStore flow
- **T7:** `TASK_07_testing_helpers.md` (depends: T4) -- Extend testing.py with detailed-word table drop/reset helpers

### database_cache package (working directory: `packages/database_cache/`)

- **T8:** `TASK_08_cache_local_store.md` (depends: T1) -- Define cache-side port, local SQLite store, and queries for detailed-word caching
- **T9:** `TASK_09_cache_service_and_tests.md` (depends: T8, T5) -- Implement `DetailedWordCacheService` with unit and integration tests

## Dependency graph (DAG)

```
T1 --> T2 --> T3 --> T4 --> T5 --> T6
                      |          |
                      v          v
                      T7         T9
                      
T1 --> T8 --> T9
```

- T1 -> T2 (models/protocols needed by backend abstract)
- T2 -> T3 (DDL and abstract methods needed before wiring)
- T3 -> T4 (tables must be creatable before Neon CRUD impl)
- T4 -> T5 (backend impl needed for store)
- T4 -> T7 (backend impl needed for test helpers)
- T5 -> T6 (store needed for e2e tests)
- T1 -> T8 (DetailedWordRecord model needed by cache)
- T8, T5 -> T9 (local store + remote store both needed)

## Execution plan

### Critical path
- T1 -> T2 -> T3 -> T4 -> T5 -> T6

### Parallel tracks (lanes)
- **Lane A** (database core): T1 -> T2 -> T3 -> T4 -> T5 -> T6
- **Lane B** (database test helpers): T7 (after T4, parallel with T5/T6)
- **Lane C** (cache): T8 (after T1, parallel with T2-T4) -> T9 (after T5 + T8)

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development uses testing/development databases via `DATABASE_URL` from Doppler env.
- **Shared resource isolation**: Tests use UUID-based data isolation (unique user_id/word data per test). Integration tests use advisory locks. No port/socket conflicts.
- **Migration deliverable**: The `word_details_<src>_<tgt>` table is created via `CREATE TABLE IF NOT EXISTS` in `create_tables()`. Production callers will get the table on next bootstrap. No destructive migration needed.
- **Cache file isolation**: Detailed-word cache uses pair-scoped SQLite files (e.g., `nl_ru_details.db`) separate from existing user-scoped practice cache files.

## Definition of Done (DoD)

All items must be true:

- All 9 tasks completed and verified
- `make check` passes in `packages/database/` (ruff format, ruff check, pylint 200-line limit, unit/integration/e2e tests)
- `make check` passes in `packages/database_cache/` (ruff format, ruff check, pylint 200-line limit, unit/integration tests)
- `make check` passes in parent repo (jscpd zero-tolerance duplication)
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches module spec (FR-11 through FR-14 for database, FR-11 through FR-15 for cache)
- Zero legacy tolerance (no dead code; codebase in sync with spec)
- No errors are silenced (no swallowed exceptions)
- Requirements/architecture docs unchanged
- Production database untouched; all development against testing DB only
- No file exceeds 200 lines
- All new functionality is purely additive -- existing behavior unchanged

## Risks + mitigations

- **Risk**: `_queries.py` is at 188 lines -- cannot add DDL inline.
  - **Mitigation**: T2 creates a new `_queries_detailed.py` file for all detailed-word SQL. T3 adds only a single import+call to wire the DDL into `create_tables()`.

- **Risk**: `neon.py` is at 187 lines -- cannot add methods inline.
  - **Mitigation**: T4 creates a new `_neon_detailed.py` file (following the `_neon_exercise.py` pattern). T3 adds only a minimal import+call to `create_tables()`.

- **Risk**: `abstract.py` is at 170 lines -- adding new abstract methods could push it close.
  - **Mitigation**: T2 creates a new `_abstract_detailed.py` mixin or separate ABC for detailed-word backend methods. The main `AbstractBackend` is NOT modified.

- **Risk**: `extract_word_details` package does not exist yet -- protocol types must be designed without a real implementation.
  - **Mitigation**: T1 defines minimal `DetailedWordExtractorPort` protocol and `DetailedWordRecord` model following the same pattern as `RemoteDeletePort` in database_cache. The contract is driven by the extractor module spec (FR-1, FR-9).

- **Risk**: Schema registry/versioning is complex and the extractor isn't built yet.
  - **Mitigation**: V1 uses a simple `schema_key` (string like "nl_ru_noun") and `schema_version` (integer) approach. Validation is a payload-is-dict check plus version comparison. Full schema parsing deferred to extractor implementation.

- **Risk**: `mock_backend.py` is at 173 lines -- adding detailed-word mock methods could push it over 200.
  - **Mitigation**: T5 adds the mock in a new `mock_detailed_backend.py` file, not in the existing mock.

## Migration plan

The `word_details_<src>_<tgt>` table is created via `CREATE TABLE IF NOT EXISTS` DDL executed by `create_tables()`. This is safe to run against production -- it adds the table without affecting existing tables. No data migration needed.

## Rollback / recovery notes

- All new code is purely additive -- existing callers are not affected.
- If rollback needed: revert the commits. The `word_details_<src>_<tgt>` table can be dropped manually if desired, but leaving it empty is harmless.

## Sources used

- Requirements: `packages/database/docs/module-spec.md`, `packages/database_cache/docs/module-spec.md`, `packages/extract_word_details/docs/module-spec.md`
- Code read:
  - `packages/database/src/nl_processing/database/` -- all source files
  - `packages/database/tests/` -- all test files and conftest
  - `packages/database_cache/src/nl_processing/database_cache/` -- all source files
  - `packages/database_cache/tests/` -- test structure
  - `packages/core/src/nl_processing/core/models.py`, `ports.py`

## Contract summary

### What (requirements)
- FR-11-14 (database): DetailedWordStore with pair-specific persistence, read-through extraction, and fail-fast validation
- FR-5 (database): create_tables() includes detailed-word table
- FR-11-15 (cache): DetailedWordCacheService with pair-scoped SQLite, read-through fetch, schema invalidation, explicit failure surfacing

### How (architecture)
- New `DetailedWordRecord` model and `DetailedWordExtractorPort` protocol in database package
- New `_abstract_detailed.py` for backend ABC, `_queries_detailed.py` for DDL/SQL, `_neon_detailed.py` for Neon impl
- New `detailed_word_store.py` for public `DetailedWordStore` class
- Minimal wiring in `neon.py` `create_tables()` for DDL execution
- New `detailed_local_store.py`, `_detailed_queries.py`, `detailed_cache_service.py` in database_cache
- New `ports.py` extension or separate `_detailed_ports.py` in database_cache for `RemoteDetailedWordPort`

## Impact inventory (implementation-facing)

- **Module**: `database` -- `src/nl_processing/database/` and `src/nl_processing/database/backend/`
- **Module**: `database_cache` -- `src/nl_processing/database_cache/`
- **Interfaces**: `DetailedWordStore.get_details()`, `DetailedWordStore.get_or_extract_details()`, `DetailedWordCacheService.get_or_fetch_details()`
- **Data model**: New `word_details_<src>_<tgt>` table (Neon), new pair-scoped SQLite tables (local cache)
- **External services**: Neon PostgreSQL via `asyncpg` (existing), SQLite via `aiosqlite` (existing)
- **Test directories**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`, `tests/unit/database_cache/`, `tests/integration/database_cache/`
