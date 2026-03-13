---
Task ID: T5
Title: Implement `DetailedWordCacheService` in `database_cache` with pair-scoped SQLite and schema-version invalidation
Sprint: 2026-03-13_extract-word-details
Module: database_cache
Depends on: T1, T4
Parallelizable: no (requires T1 and T4 to be complete)
---

## Goal / value

After this task, `database_cache` exposes a fully functional `DetailedWordCacheService` that provides pair-scoped read-through caching for detailed-word records. It uses a dedicated SQLite file (separate from the user-scoped practice cache), validates schema versions on read, invalidates incompatible rows, and surfaces remote failures explicitly. Unit, integration, and e2e tests verify the full contract. `make check` passes.

## Context (contract mapping)

- Database cache spec: `packages/database_cache/docs/module-spec.md` — FR-11 (DetailedWordCacheService API), FR-12 (dedicated pair-scoped SQLite), FR-13 (read-through cache), FR-14 (schema version invalidation), FR-15 (remote failure transparency), DEC-7 (pair-scoped not user-scoped), DEC-8 (read-through), DEC-9 (schema invalidation), BR-7 (pair-scoped user-independent), BR-8 (round-trip schema registry), BR-9 (incompatible rows invalid)
- Related: `packages/database/docs/module-spec.md` — IF-2, DEC-11 (cache consumes DetailedWordStore contract)

## Preconditions

- T1 complete: schema registry and serializer contract exist in `extract_word_details`
- T4 complete: `DetailedWordStore` exists in `database` with `get_details()` and `get_or_extract_details()`
- Existing `database_cache` package is fully functional for practice-cache concerns

## Non-goals

- Modifying existing `DatabaseCacheService` behavior
- Implementing automatic cache eviction (deferred per OQ-1)
- Supporting the practice-cache lifecycle for detailed words (no `init()`, no TTL — read-through only)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `packages/database_cache/src/nl_processing/database_cache/` — source code
- `packages/database_cache/tests/` — tests
- `packages/database_cache/pyproject.toml` — if a new dependency is needed
- `packages/database_cache/Makefile` — if PYTHONPATH needs updating

**FORBIDDEN — this task must NEVER touch:**

- `packages/extract_word_details/` (T1/T2/T3)
- `packages/database/` (T4)
- `packages/core/`
- Root configs

**Test scope:**

- Tests go in: `packages/database_cache/tests/unit/`, `tests/integration/`, `tests/e2e/`
- Test command: `make check` in `packages/database_cache/`

## Touched surface (expected files / modules)

**New files to create:**

- `src/nl_processing/database_cache/detailed_cache.py` — `DetailedWordCacheService` class
- `src/nl_processing/database_cache/_detailed_local_store.py` — pair-scoped SQLite store for detailed words
- `src/nl_processing/database_cache/_detailed_queries.py` — SQLite DDL and query templates for detailed-word cache tables
- `src/nl_processing/database_cache/detailed_ports.py` — protocol for the remote detailed-word store (if not already using `database.detailed_ports`)
- `tests/unit/database_cache/test_detailed_cache.py` — unit tests with mock remote store
- `tests/integration/database_cache/test_detailed_cache_integration.py` — integration tests with real SQLite
- `tests/e2e/database_cache/test_detailed_cache_e2e.py` — e2e tests with real remote backend

**Files to modify:**

- `packages/database_cache/pyproject.toml` — add `nl-processing-extract-word-details` as dev dependency (for schema registry access in tests)
- `packages/database_cache/Makefile` — add `../extract_word_details/src` to PYTHONPATH

## Dependencies and sequencing notes

- Depends on T1 for schema registry (used for schema_version validation)
- Depends on T4 for `DetailedWordStore` (the remote backend contract)
- The `DetailedWordCacheService` injects the remote store via protocol, so it's testable with mocks independently

## Third-party / library research (mandatory for any external dependency)

- **Library**: `aiosqlite` v0.20 (already in repo: `>=0.20,<1`)
  - **Relevant docs**: https://aiosqlite.omnilib.dev/en/stable/
  - **API**: `aiosqlite.connect(path)`, `connection.execute(sql, params)`, `connection.commit()`, `connection.fetchone()`, `connection.fetchall()`
  - **Usage**: Same pattern as existing `_local_store_base.py`. Open connection, create tables, execute queries.
  - **Gotcha**: SQLite uses `?` parameter placeholders (not `$1`). JSONB is not native — store JSON as TEXT.

- **Schema registry interaction**: The `DetailedWordCacheService` needs to check schema version compatibility. It imports the schema registry from `extract_word_details` (available via PYTHONPATH in dev). At runtime, the cache stores `schema_key` and `schema_version` alongside the payload. On read, it checks if the stored version is still compatible via the registry's `is_compatible()` method. If incompatible, it deletes the local row and refetches from remote.

  **Dependency note**: `database_cache` already depends on `database`. For schema registry access, it needs `extract_word_details` in PYTHONPATH during development. The `detailed_cache.py` can accept the registry as an optional injection (for testability) or import it. Since the `extract_word_details` package is in PYTHONPATH at development time, direct import is acceptable. For production, the schema registry must be available — this means `extract_word_details` should be installed alongside `database_cache` when the cache is used for detailed words.

  **Practical approach**: Define a `SchemaVersionChecker` protocol in `detailed_ports.py`:
  ```python
  class SchemaVersionChecker(Protocol):
      def is_compatible(self, schema_key: str, schema_version: int) -> bool: ...
  ```
  Inject this into `DetailedWordCacheService`. In production, pass the real `SCHEMA_REGISTRY` from `extract_word_details`. In tests, pass a mock.

## Implementation steps (developer-facing)

1. **Create `_detailed_queries.py`** — SQLite DDL and queries:
   ```python
   CREATE_DETAILED_WORDS_TABLE = """
       CREATE TABLE IF NOT EXISTS cached_detailed_words (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           source_word TEXT NOT NULL,
           word_type TEXT NOT NULL,
           schema_key TEXT NOT NULL,
           schema_version INTEGER NOT NULL,
           payload TEXT NOT NULL,
           cached_at TEXT NOT NULL,
           UNIQUE(source_word, word_type)
       )
   """

   INSERT_OR_REPLACE_DETAILED = """
       INSERT OR REPLACE INTO cached_detailed_words
       (source_word, word_type, schema_key, schema_version, payload, cached_at)
       VALUES (?, ?, ?, ?, ?, ?)
   """

   SELECT_DETAILED = """
       SELECT source_word, word_type, schema_key, schema_version, payload
       FROM cached_detailed_words
       WHERE source_word = ? AND word_type = ?
   """

   DELETE_DETAILED = """
       DELETE FROM cached_detailed_words
       WHERE source_word = ? AND word_type = ?
   """
   ```

2. **Create `detailed_ports.py`** — protocol for remote store and schema checker:
   ```python
   class RemoteDetailedWordStorePort(Protocol):
       async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]: ...

   class SchemaVersionChecker(Protocol):
       def is_compatible(self, schema_key: str, schema_version: int) -> bool: ...
   ```

3. **Create `_detailed_local_store.py`** — pair-scoped SQLite store:
   - Class: `DetailedLocalStore`
   - Constructor: `__init__(self, db_path: str)` — stores path, connection initially None
   - `open()` — open aiosqlite connection, create tables, enable WAL mode
   - `close()` — close connection
   - `get_cached_detail(source_word: str, word_type: str) -> dict | None` — fetch single row
   - `get_cached_details_batch(keys: list[tuple[str, str]]) -> list[dict]` — fetch batch
   - `upsert_cached_detail(source_word, word_type, schema_key, schema_version, payload_json)` — insert or replace
   - `delete_cached_detail(source_word, word_type)` — delete a single row (for invalidation)
   - Follow the same base pattern as `_local_store_base.py` but as a standalone class (not sharing the practice-cache connection per FR-12/DEC-7)

4. **Create `detailed_cache.py` — `DetailedWordCacheService`**:

   Constructor:
   - Parameters: `source_language: Language`, `target_language: Language`, `remote_store: RemoteDetailedWordStorePort | None = None`, `local_store: DetailedLocalStore | None = None`, `schema_checker: SchemaVersionChecker | None = None`, `cache_dir: str | None = None`
   - If `local_store is None`, create one at `{cache_dir}/{src}_{tgt}_details.db`
   - If `remote_store is None`, create a `DetailedWordStore` from `database` as the default remote backend
   - Store schema_checker for version validation

   `get_or_fetch_details(words: list[Word]) -> list[DetailedWordRecord]`:
   - Open local store if not already open
   - For each word, check local cache: `local_store.get_cached_detail(word.normalized_form, word.word_type.value)`
   - For each local hit, check schema version compatibility (if `schema_checker` is provided):
     - If `schema_checker.is_compatible(row.schema_key, row.schema_version)` is False, delete the local row and treat as a miss
   - Collect local hits and misses
   - If there are misses:
     - Call `remote_store.get_or_extract_details(misses)` — this may raise
     - If remote call fails, re-raise the exception (FR-15) — do NOT mutate local state on failure
     - For each returned record, persist locally via `local_store.upsert_cached_detail()`
   - Merge hits and newly-fetched records in supported-input order
   - Return `list[DetailedWordRecord]`

5. **Update `pyproject.toml`** if needed — `nl-processing-extract-word-details` as a dev dependency.

6. **Update `Makefile` PYTHONPATH** to include `../extract_word_details/src`.

7. **Write unit tests (`test_detailed_cache.py`)**:
   - Test `get_or_fetch_details([])` returns `[]`
   - Test all hits (local cache has all entries) — remote store NOT called
   - Test all misses (local cache empty) — remote store called, results cached
   - Test mixed hits/misses — remote called only for misses
   - Test schema version invalidation: local row exists but is_compatible returns False → row deleted, remote fetched
   - Test remote failure: remote store raises → exception propagated, local state unchanged (FR-15)
   - Test order preservation: results match supported-input order
   - Use mock local store and mock remote store

8. **Write integration tests (`test_detailed_cache_integration.py`)**:
   - Use real SQLite (in temp dir)
   - Test full lifecycle: cache empty → fetch → cache populated → second fetch is a hit
   - Test schema invalidation with real SQLite deletion and re-fetch
   - Use mock remote store

9. **Write e2e tests (`test_detailed_cache_e2e.py`)**:
   - Full flow with real remote backend (Neon DB via Doppler) and real SQLite
   - Insert a source word in Neon → use `DetailedWordStore` as remote → `DetailedWordCacheService` fetches and caches
   - Second call returns from cache without remote call
   - Use mock extractor in the remote `DetailedWordStore`

10. **Verify**: Run `make check` in `packages/database_cache/`. All tests pass (existing + new).

## Production safety constraints (mandatory)

- **Database operations**: Integration/e2e tests use the test Neon DB via `doppler run --`. Local SQLite files are created in `tempfile.mkdtemp()` during tests.
- **Production cache isolation**: The pair-scoped SQLite file (`{src}_{tgt}_details.db`) is in a configurable directory. Tests never write to the production cache directory.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the same pattern as `_local_store_base.py` for SQLite operations. Reuse `DetailedWordRecord` from `database.detailed_models`. Reuse the `aiosqlite` connection management pattern.
- **Correct libraries only**: `aiosqlite>=0.20,<1` — already in `database_cache` package.
- **Correct file locations**: New files follow existing module structure.
- **No regressions**: Existing `DatabaseCacheService` tests must continue passing.

## Error handling + correctness rules (mandatory)

- Remote fetch failure must propagate the exception to the caller and NOT modify local cache state (FR-15)
- Incompatible schema version rows must be deleted locally and refetched — never served to callers (BR-9)
- SQLite errors must raise `CacheStorageError`, not be swallowed
- Missing remote store (None) when cache miss occurs must raise explicitly, not return partial results

## Zero legacy tolerance rule (mandatory)

- New `DetailedWordCacheService` is additive — no existing code paths superseded
- No fallback data for failed remote fetches (FR-15)
- No stale schema-incompatible rows served (FR-14)

## Acceptance criteria (testable)

1. `DetailedWordCacheService` creates a pair-scoped SQLite file separate from the user-scoped practice-cache file (FR-12).
2. `get_or_fetch_details()` returns cached records for local hits without remote calls.
3. `get_or_fetch_details()` fetches from remote for local misses, caches results, and returns them.
4. Local rows with incompatible schema versions are invalidated and refetched (FR-14).
5. Remote fetch failures propagate to the caller without mutating local state (FR-15).
6. Results are in supported-input order.
7. All existing `database_cache` tests still pass.
8. `make check` passes in `packages/database_cache/`.
9. No file exceeds 200 lines.

## Verification / quality gates

- [x] Unit tests added (all cache paths: hit, miss, mixed, invalidation, remote failure)
- [x] Integration tests added (real SQLite lifecycle)
- [x] E2E tests added (real remote backend + real SQLite)
- [x] Existing tests unbroken
- [x] Linters/formatters pass
- [x] No new warnings
- [x] Negative-path tests (remote failure, schema incompatibility)
- [x] No file exceeds 200 lines

## Edge cases

- `get_or_fetch_details([])` — return `[]`, no local or remote operations
- All words have incompatible cached versions — all deleted and refetched
- Remote returns fewer results than requested (some POS unsupported) — cache only stores what was returned
- Two concurrent calls for the same word — SQLite `INSERT OR REPLACE` handles this safely
- Cache file does not exist yet — `open()` creates it
- `schema_checker` is None — skip version checking, serve whatever is cached (useful for tests or when the registry is not available)

## Notes / risks

- **Schema registry availability**: The `DetailedWordCacheService` needs a `SchemaVersionChecker` for proper invalidation. If the checker is not provided (None), the cache skips version validation and serves whatever is stored. This is acceptable for V1 where schema versions don't change. When versions do change, callers must inject the checker.
- **File separation from practice cache**: The practice cache uses `{user}_{src}_{tgt}.db`. The detailed cache uses `{src}_{tgt}_details.db`. These are separate files in the same directory. No collision risk.
- **Payload storage**: JSON payload is stored as TEXT in SQLite (no native JSONB). `json.dumps()` on write, `json.loads()` on read.
