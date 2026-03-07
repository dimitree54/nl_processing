---
Sprint ID: `2026-03-07_database-cache-extraction`
Sprint Goal: `Remove legacy CachedDatabaseService, fix discrepancies between database/database_cache docs and implementation, and harden apply_score_delta.`
Sprint Type: `module`
Module: `database`
Status: `planning`
Owners: `Developer`
---

## Goal

Remove the legacy `CachedDatabaseService` from the `database` module, fix six code/doc discrepancies (missing delta validation, TOCTOU atomicity, FR21 warning logging, stale module structure in docs, phantom Protocol in docs), and sync `database_cache` docs to match the actual `database` API. After this sprint, `make check` is green, there is zero legacy caching code in `database`, and both modules' docs reflect reality.

## Module Scope

### What this sprint implements
- Module: `database` (code changes) + `database` and `database_cache` docs (doc-only changes)

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED -- this sprint may ONLY touch:**
- `nl_processing/database/cached_service.py` -- delete
- `nl_processing/database/exercise_progress.py` -- delta validation + atomicity fix
- `nl_processing/database/service.py` -- FR21 warning logging
- `nl_processing/database/backend/abstract.py` -- new atomic method
- `nl_processing/database/backend/neon.py` -- new atomic method implementation
- `nl_processing/database/backend/_neon_exercise.py` -- atomic apply helper
- `nl_processing/database/docs/architecture_database.md` -- doc sync
- `nl_processing/database/docs/prd_database.md` -- doc sync
- `nl_processing/database_cache/docs/architecture_database_cache.md` -- doc sync
- `nl_processing/database_cache/docs/prd_database_cache.md` -- doc sync (if needed)
- `tests/unit/database/conftest.py` -- remove CachedDatabaseService fixture
- `tests/unit/database/test_service.py` -- remove CachedDatabaseService tests, add FR21 test
- `tests/unit/database/test_exercise_progress.py` -- add delta validation + atomicity tests
- `vulture_whitelist.py` -- remove CachedDatabaseService entries, add new entries if needed

**FORBIDDEN -- this sprint must NEVER touch:**
- Any module outside `database` / `database_cache` docs
- Bot code
- `nl_processing/database_cache/` source files (only docs exist; implementation is a future sprint)
- Integration or e2e test files (unless strictly required by a code change -- see task notes)
- `docs/planning-artifacts/` (shared architecture, shared PRD)

### Test Scope
- **Test directory**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- **Verification command**: `make check` (full pipeline: ruff, pylint, vulture, jscpd, unit, integration, e2e)
- After every task, `make check` must be 100% green.

## Interface Contract

### Public interface (unchanged)

```python
class DatabaseService:
    async def add_words(self, words: list[Word]) -> AddWordsResult: ...
    async def get_words(self, *, word_type=None, limit=None, random=False) -> list[WordPair]: ...
    @classmethod
    async def create_tables(cls, exercise_slugs=None) -> None: ...

class ExerciseProgressStore:
    async def increment(self, source_word_id: int, exercise_type: str, delta: int) -> None: ...
    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]: ...
    async def export_remote_snapshot(self) -> list[ScoredWordPair]: ...
    async def apply_score_delta(self, event_id: str, source_word_id: int, exercise_type: str, delta: int) -> None: ...
```

### Removed interface

```python
# DELETED -- all caching logic moves to database_cache module
class CachedDatabaseService: ...
```

## Scope

### In
- T1: Remove `CachedDatabaseService` (code + tests + vulture whitelist)
- T2: Add delta validation to `apply_score_delta` (FR32)
- T3: Make `apply_score_delta` atomic (fix TOCTOU race)
- T4: Add FR21 missing-translation warning logging
- T5: Sync `database` docs with implementation
- T6: Sync `database_cache` docs with actual `database` API

### Out
- Implementing the `database_cache` module (future sprint)
- Changing `database` public API signatures
- Changing integration or e2e tests beyond what is forced by code deletion
- Adding new features to `database`

## Inputs (contracts)

- Requirements: `nl_processing/database/docs/prd_database.md`
- Architecture: `nl_processing/database/docs/architecture_database.md`
- `database_cache` Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md`
- `database_cache` PRD: `nl_processing/database_cache/docs/prd_database_cache.md`
- Prototype codebase: all `nl_processing/database/` source files + tests

## Change digest

- **Requirement deltas**:
  - FR32 (`delta` limited to +1/-1) is documented but not enforced in `apply_score_delta` -- fix.
  - FR21 (missing translation warning) is documented but not implemented -- fix.
- **Architecture deltas**:
  - `architecture_database.md` module structure omits `_neon_exercise.py` and `_queries.py` -- fix.
  - `architecture_database.md` cache-support section describes a `DatabaseCacheSyncBackend` Protocol with methods that don't exist (`export_user_word_pairs`, `export_user_scores`) -- fix to match actual API.
  - `architecture_database_cache.md` Remote Integration Contract specifies `DatabaseCacheSyncBackend` Protocol with phantom types (`RemoteWordPairRecord`, `RemoteScoreRecord`) and phantom methods -- fix to match actual `ExerciseProgressStore` API.
  - `cached_service.py` listed in module structure -- remove from docs after deletion.

## Task list (dependency-aware)

- **T1:** `TASK_01_remove_cached_service.md` (depends: --) (parallel: no) -- Remove CachedDatabaseService entirely
- **T2:** `TASK_02_apply_delta_validation.md` (depends: --) (parallel: yes, with T1) -- Add delta validation to apply_score_delta
- **T3:** `TASK_03_apply_delta_atomicity.md` (depends: T2) (parallel: no) -- Make apply_score_delta atomic
- **T4:** `TASK_04_fr21_missing_translation_warning.md` (depends: --) (parallel: yes, with T1, T2) -- Add FR21 warning logging
- **T5:** `TASK_05_sync_database_docs.md` (depends: T1, T2, T3, T4) (parallel: no) -- Sync database docs with implementation
- **T6:** `TASK_06_sync_database_cache_docs.md` (depends: T5) (parallel: no) -- Sync database_cache docs with actual database API

## Dependency graph (DAG)

```
T1 ─────────────────────┐
T2 ──┬──────────────────┤
     T3 ────────────────┤
T4 ─────────────────────┼─> T5 ──> T6
```

## Execution plan

### Critical path
T2 -> T3 -> T5 -> T6

### Parallel tracks (lanes)
- **Lane A**: T1 (independent code deletion)
- **Lane B**: T2 -> T3 (apply_score_delta hardening)
- **Lane C**: T4 (FR21 logging, independent)
- **Lane D** (serial): T5 (docs sync, waits for all code tasks) -> T6

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development and testing uses testing/development databases (Doppler `dev` environment for integration/e2e).
- **Shared resource isolation**: No new ports, sockets, or file paths introduced. Changes are to in-process logic and documentation only.
- **Migration deliverable**: N/A -- no data model changes. The atomicity fix (T3) changes query execution strategy (transaction wrapping) but does not alter the schema.

## Definition of Done (DoD)

All items must be true:

- `make check` is 100% green (ruff format, ruff check, pylint 200-line, vulture, jscpd, unit tests, integration tests, e2e tests)
- `nl_processing/database/cached_service.py` no longer exists
- `vulture_whitelist.py` has no `CachedDatabaseService` references
- `apply_score_delta` validates delta is +1 or -1
- `apply_score_delta` check-increment-mark is atomic (single transaction)
- `get_words()` logs a warning when untranslated words are excluded
- `architecture_database.md` module structure matches reality (includes `_neon_exercise.py`, `_queries.py`, no `cached_service.py`)
- `architecture_database.md` cache-support section matches actual API (`export_remote_snapshot`, `apply_score_delta` with instance params)
- `architecture_database_cache.md` Remote Integration Contract matches actual `database` API
- Zero legacy: no dead code, no deprecated paths, no phantom types in docs
- No files outside the ALLOWED list were touched
- Production database untouched

## Risks + mitigations

- **Risk**: Removing `CachedDatabaseService` could break external consumers we haven't identified.
  - **Mitigation**: Grep confirmed only test files + vulture whitelist reference it. The README mentions it but is out of scope for this sprint (doc-only, shared infra).
- **Risk**: Atomic transaction in `apply_score_delta` could introduce deadlocks under concurrent access.
  - **Mitigation**: The transaction scope is narrow (check + upsert + insert in same connection). asyncpg transactions are connection-scoped. Risk is minimal for single-user patterns.
- **Risk**: `_neon_exercise.py` line count may exceed 200 lines after adding the atomic helper.
  - **Mitigation**: The file is currently 92 lines; the new function adds ~15 lines. Well within limits.

## Migration plan (if data model changes)

N/A -- no data model changes in this sprint.

## Rollback / recovery notes

- Revert the git commits from this sprint.
- All changes are backward-compatible code deletions, validation additions, and doc updates.

## Task validation status

- Per-task validation order: `T1` -> `T2` -> `T3` -> `T4` -> `T5` -> `T6`
- Validator: `task-checker`
- Outcome: `pending`
- Notes: Each task validated individually before proceeding to next.

## Sources used

- Requirements: `nl_processing/database/docs/prd_database.md`
- Architecture: `nl_processing/database/docs/architecture_database.md`
- `database_cache` docs: `nl_processing/database_cache/docs/architecture_database_cache.md`, `nl_processing/database_cache/docs/prd_database_cache.md`
- Code read:
  - `nl_processing/database/cached_service.py` (82 lines)
  - `nl_processing/database/service.py` (157 lines)
  - `nl_processing/database/exercise_progress.py` (167 lines)
  - `nl_processing/database/backend/abstract.py` (117 lines)
  - `nl_processing/database/backend/neon.py` (190 lines)
  - `nl_processing/database/backend/_neon_exercise.py` (92 lines)
  - `nl_processing/database/backend/_queries.py` (174 lines)
  - `nl_processing/database/models.py` (19 lines)
  - `nl_processing/database/exceptions.py` (6 lines)
  - `nl_processing/database/logging.py` (5 lines)
  - `nl_processing/database/testing.py` (111 lines)
  - `tests/unit/database/conftest.py` (187 lines)
  - `tests/unit/database/test_service.py` (160 lines)
  - `tests/unit/database/test_exercise_progress.py` (146 lines)
  - `vulture_whitelist.py` (125 lines)

## Contract summary

### What (requirements)
- FR32: delta limited to +1/-1 in `apply_score_delta` (currently unenforced)
- FR21: missing translations logged as warnings (currently unimplemented)
- FR38-40: idempotent `apply_score_delta` must be atomic (currently TOCTOU-racy)
- Legacy `CachedDatabaseService` must be removed (all caching to `database_cache`)

### How (architecture)
- `apply_score_delta` wrapped in a single transaction (backend-level atomic method)
- `get_words()` compares returned-row count to user-word count, logs warning on mismatch
- docs updated to reflect actual code structure and API signatures
- `cached_service.py` deleted, vulture whitelist cleaned

## Impact inventory (implementation-facing)

- **Module**: `database` (`nl_processing/database/`)
- **Interfaces**: `ExerciseProgressStore.apply_score_delta` (behavior tightened, not signature-changed)
- **Data model**: unchanged
- **External services**: Neon PostgreSQL (existing, no new connections)
- **Test directory**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
