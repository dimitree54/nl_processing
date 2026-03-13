---
Task ID: `T9`
Title: `Implement DetailedWordCacheService with unit and integration tests`
Sprint: `2026-03-13_detailed-words`
Module: `database_cache`
Depends on: `T8, T5`
Parallelizable: `no`
---

## Goal / value

Implement the public `DetailedWordCacheService` class with `get_or_fetch_details()` method. This is the main deliverable of the sprint's cache side -- the pair-scoped read-through cache for detailed-word records. After this task, callers can fetch detailed-word records with local caching, schema version invalidation, and explicit failure surfacing.

## Context (contract mapping)

- Requirements: `packages/database_cache/docs/module-spec.md` -- FR-11 (DetailedWordCacheService), FR-13 (get_or_fetch_details read-through), FR-14 (schema version invalidation), FR-15 (remote fetch failures leave cache unchanged), DEC-8 (read-through), DEC-9 (invalidate incompatible)
- Pattern reference: `packages/database_cache/src/nl_processing/database_cache/service.py` (existing cache service pattern)

## Preconditions

- T8 completed: `DetailedWordLocalStore`, `RemoteDetailedWordPort`, and `_detailed_queries.py` exist.
- T5 completed: `DetailedWordStore` exists (used as the default remote store and validates the protocol compatibility).
- T1 completed: `DetailedWordRecord` model exists.

## Non-goals

- No real Neon integration tests (the cache tests use fake remote stores).
- No modification to existing `DatabaseCacheService`, `CacheSyncer`, or `LocalStore`.
- No modification to existing test files.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `packages/database_cache/src/nl_processing/database_cache/` -- new file: `detailed_cache_service.py`
- `packages/database_cache/tests/unit/database_cache/` -- new test files
- `packages/database_cache/tests/integration/database_cache/` -- new test files

**FORBIDDEN -- this task must NEVER touch:**
- `packages/database_cache/src/nl_processing/database_cache/service.py` (existing)
- `packages/database_cache/src/nl_processing/database_cache/local_store.py` (existing)
- `packages/database_cache/src/nl_processing/database_cache/sync.py` (existing)
- Any existing test files
- `packages/database/` source code (read-only import)
- `src/nl_processing/core/` or any core package file

**Test scope:**
- Tests go in: `tests/unit/database_cache/`, `tests/integration/database_cache/`
- Test command: `make check` (in `packages/database_cache/`)
- Working directory: `packages/database_cache/`

## Touched surface (expected files / modules)

**New files to create:**
- `src/nl_processing/database_cache/detailed_cache_service.py` (~80-130 lines) -- Public cache service
- `tests/unit/database_cache/test_detailed_cache_service.py` (~100-150 lines) -- Unit tests with fake remote
- `tests/integration/database_cache/test_detailed_cache.py` (~80-120 lines) -- Integration tests with SQLite persistence

## Dependencies and sequencing notes

- Depends on T8 for `DetailedWordLocalStore`, `RemoteDetailedWordPort`, and `_detailed_queries.py`.
- Depends on T5 for `DetailedWordStore` (validates protocol compatibility).
- This is the last task in the sprint.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `aiosqlite` -- already used. Same version.
- **Library**: `json` -- standard library, for payload de/serialization.
- No new dependencies.

## Implementation steps (developer-facing)

1. **Create `src/nl_processing/database_cache/detailed_cache_service.py`:**

   ```python
   class DetailedWordCacheService:
       """Pair-scoped read-through cache for detailed-word records."""

       def __init__(
           self,
           source_language: Language,
           target_language: Language,
           remote_store: RemoteDetailedWordPort | None = None,
           local_store: DetailedWordLocalStore | None = None,
           cache_dir: str | None = None,
       ) -> None:
           self._source_language = source_language
           self._target_language = target_language
           src = source_language.value
           tgt = target_language.value
           base = cache_dir or tempfile.gettempdir()
           self._db_path = f"{base}/{src}_{tgt}_details.db"
           self._remote = remote_store
           self._local: DetailedWordLocalStore | None = local_store
           self._initialized = False

       async def init(self) -> None:
           """Open local store and prepare for reads."""
           if self._local is None:
               self._local = DetailedWordLocalStore(self._db_path)
           await self._local.open()
           self._initialized = True

       async def get_or_fetch_details(
           self, words: list[Word],
       ) -> list[DetailedWordRecord]:
           """Return cached hits + fetch remote misses.

           FR-13: Read-through cache behavior.
           FR-14: Invalidate incompatible local schema versions.
           FR-15: Remote failures leave local cache unchanged.
           """
           self._ensure_ready()
           assert self._local is not None
           if not words:
               return []

           # Build lookup keys
           keys = [(w.normalized_form, w.word_type.value) for w in words]

           # Check local cache
           cached_rows = await self._local.get_cached_details(keys)
           cached_map: dict[tuple[str, str], DetailedWordRecord] = {}
           for row in cached_rows:
               record = _row_to_record(row)
               cached_map[(record.source_word, record.word_type)] = record

           # Identify misses
           misses = [w for w in words if (w.normalized_form, w.word_type.value) not in cached_map]

           if misses and self._remote is not None:
               # FR-15: Remote failures surface explicitly
               remote_records = await self._remote.get_or_extract_details(misses)
               for record in remote_records:
                   # FR-14: Invalidate incompatible local versions
                   await self._local.invalidate_incompatible(
                       record.source_word, record.word_type, record.schema_version,
                   )
                   # Persist locally
                   await self._local.upsert_detail(
                       record.source_word, record.word_type,
                       record.schema_key, record.schema_version,
                       json.dumps(record.payload),
                   )
                   cached_map[(record.source_word, record.word_type)] = record
           elif misses and self._remote is None:
               # No remote store to fetch from; return only local hits
               pass

           # Return in input order, skip words not in cache or remote
           result = []
           for w in words:
               key = (w.normalized_form, w.word_type.value)
               if key in cached_map:
                   result.append(cached_map[key])
           return result

       def _ensure_ready(self) -> None:
           if not self._initialized or self._local is None:
               raise CacheNotReadyError("DetailedWordCacheService not initialized -- call init() first")
   ```

   Note the helper `_row_to_record()` can be inline or a module-level function.

2. **Create `tests/unit/database_cache/test_detailed_cache_service.py`:**

   Define a `FakeRemoteStore` implementing `RemoteDetailedWordPort`:
   ```python
   class FakeRemoteStore:
       def __init__(self, records: list[DetailedWordRecord]) -> None:
           self._records = {(r.source_word, r.word_type): r for r in records}
           self.call_count = 0

       async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]:
           self.call_count += 1
           return [self._records[(w.normalized_form, w.word_type.value)]
                   for w in words if (w.normalized_form, w.word_type.value) in self._records]
   ```

   Also define a `FailingRemoteStore` that raises an exception.

   Test cases:
   - **Not initialized**: `get_or_fetch_details()` before `init()` raises `CacheNotReadyError`.
   - **Empty input**: Returns `[]`.
   - **All local hits**: Returns cached records, remote NOT called.
   - **All misses**: Calls remote, persists locally, returns records.
   - **Mixed hits and misses**: Returns merged in input order.
   - **Second call reuses cache**: Remote called only once.
   - **Remote failure (FR-15)**: `FailingRemoteStore` raises, local cache unchanged, exception propagates.
   - **No remote store + misses**: Returns only local hits (no error for missing remote).
   - **Schema version invalidation**: Cache a row with version 1. Remote returns version 2 for the same word. Verify version 2 is cached and returned.

3. **Create `tests/integration/database_cache/test_detailed_cache.py`:**

   Integration tests with a real (temporary) SQLite file:
   - **Persistence test**: Use `DetailedWordCacheService` with `FakeRemoteStore` and a `tmp_path` SQLite. Fetch details, close service. Re-open service, verify details are still cached.
   - **Invalidation persistence test**: Cache version 1, then fetch version 2 via remote. Close and re-open. Verify version 2 is persisted.
   - **Pair-scoped isolation**: Create two services with different language pairs. Verify they don't share data.

4. **Run `make check`** in `packages/database_cache/` and verify green.

## Production safety constraints (mandatory)

- **Database operations**: Only local SQLite operations. No remote database access in tests.
- **File isolation**: Tests use `tmp_path` fixtures for SQLite files. No collision with production.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow `DatabaseCacheService` patterns for init/ensure_ready/injected dependencies.
- **Correct file locations**: New files in `src/nl_processing/database_cache/` and `tests/`.
- **No regressions**: No existing files modified.

## Error handling + correctness rules (mandatory)

- `CacheNotReadyError` raised when not initialized (same pattern as `DatabaseCacheService`).
- Remote fetch exceptions propagate to caller (FR-15). Local cache is NOT modified on remote failure.
- `CacheStorageError` for SQLite failures (same pattern as existing local store).
- No empty catch blocks. No silent error suppression.
- No synthetic fallback data on failure.

## Zero legacy tolerance rule (mandatory)

- N/A -- this task creates new code only.

## Acceptance criteria (testable)

1. `from nl_processing.database_cache.detailed_cache_service import DetailedWordCacheService` succeeds.
2. `DetailedWordCacheService(source_language=Language.NL, target_language=Language.RU)` creates a valid instance.
3. `init()` + `get_or_fetch_details([word])` returns records from remote on first call.
4. Second `get_or_fetch_details([same_word])` returns from local cache, remote NOT called.
5. Remote failure propagates and local cache is unchanged (FR-15).
6. Schema version invalidation works: version 2 replaces version 1 locally (FR-14).
7. Pair-scoped isolation: different pairs use different SQLite files (FR-12, DEC-7).
8. `CacheNotReadyError` raised before `init()`.
9. All unit and integration tests pass.
10. `make check` passes in `packages/database_cache/`.
11. All new files under 200 lines.

## Verification / quality gates

- [x] Unit tests added for happy paths and error paths
- [x] Integration tests added for SQLite persistence and invalidation
- [x] Linters/formatters pass (`make check`)
- [x] No new warnings introduced
- [x] All new files under 200 lines
- [x] Negative-path tests for CacheNotReadyError, remote failure, missing remote

## Edge cases

- Cache file doesn't exist yet: `init()` creates it via `DetailedWordLocalStore.open()`.
- All words already cached: Remote not called at all.
- Remote returns fewer records than requested (skipped POS): Only returned records are cached.
- Concurrent calls: Not required for V1 (single-caller assumption, same as `DatabaseCacheService`).
- `cache_dir` is None: Uses `tempfile.gettempdir()` (same pattern as `DatabaseCacheService`).

## Notes / risks

- **Risk**: The `DetailedWordCacheService` depends on both `database.detailed_models` and `database_cache.detailed_local_store`.
  - **Mitigation**: These are expected cross-package dependencies. `database_cache` already depends on `database`.
- **Design decision**: The cache does NOT call `init()` automatically -- callers must call `init()` explicitly (same pattern as `DatabaseCacheService`).
- **Design decision**: When `remote_store` is None and there are misses, the service returns only local hits without raising an error. This differs from `DetailedWordStore.get_or_extract_details()` which raises when extractor is missing. The cache layer is more lenient -- it degrades gracefully to local-only reads.
- **Design decision**: The file path pattern is `{cache_dir}/{src}_{tgt}_details.db` (e.g., `nl_ru_details.db`), which is pair-scoped and NOT user-scoped (matching DEC-7).
