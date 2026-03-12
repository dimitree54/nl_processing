---
Sprint ID: `2026-03-12_cache-personal-vocab`
Sprint Goal: `Add personal-vocabulary reads, progress summary, and remote-first delete to database_cache`
Sprint Type: `module`
Module: `database_cache`
---

## Goal

Extend `database_cache` to support local personal-vocabulary reads (FR-7), exercise-progress summaries (FR-8), remote-first delete (FR-9), and `added_at` persistence during refresh (FR-10). All new features read from / modify local SQLite state, with delete being the only operation that requires remote success before local mutation.

## Module Scope

### What this sprint implements

- Module: `database_cache`
- Reference to docs: `docs/module-spec.md`

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `src/nl_processing/database_cache/` — module source code
- `tests/unit/database_cache/` — unit tests
- `tests/integration/database_cache/` — integration tests
- `tests/e2e/database_cache/` — E2E tests
- `docs/sprints/sprint-cache-personal-vocab/` — this sprint's planning files

**FORBIDDEN — this sprint must NEVER touch:**
- `src/nl_processing/core/` or any `core` package file
- `src/nl_processing/database/` or any `database` package file
- Any other module's code or tests
- Bot code, configs, or infrastructure outside this module
- The full test suite (only run `tests/unit/database_cache/`, `tests/integration/database_cache/`, `tests/e2e/database_cache/`)

### Test Scope

- **Test directories**: `tests/unit/database_cache/`, `tests/integration/database_cache/`, `tests/e2e/database_cache/`
- **Test command (unit)**: `uv run pytest tests/unit/database_cache/ -x -v`
- **Test command (integration)**: `uv run pytest tests/integration/database_cache/ -x -v`
- **Test command (e2e)**: `uv run pytest tests/e2e/database_cache/ -x -v`
- **NEVER run**: `uv run pytest` (full suite) or tests from other modules

## Interface Contract

### Public interface this sprint implements

```python
# FR-7: Personal vocabulary list (local)
async def list_personal_words(self) -> list[PersonalWord]:
    """Return personal-vocabulary entries from local cache, including
    stable IDs, added_at, and per-exercise scores."""
    ...

# FR-8: Exercise progress summary (local)
async def get_progress_summary(self) -> dict[str, ExerciseProgressSummary]:
    """Return per-exercise progress stats from cached personal-vocabulary data."""
    ...

# FR-9: Delete one word (remote-first, then local prune)
async def delete_word(self, source_word_id: int) -> None:
    """Delete a word from remote, then prune local snapshot rows, scores,
    and pending score events."""
    ...

# FR-9: Delete many words (remote-first, then local prune)
async def delete_words(self, source_word_ids: list[int]) -> None:
    """Delete multiple words from remote, then prune local state."""
    ...
```

### Models consumed from `database` package (read-only, not modified)

```python
from nl_processing.database.models import PersonalWord, EnrichedWordPairSnapshot, ExerciseProgressSummary
from nl_processing.database.exceptions import WordNotFoundError
```

### Remote delete mechanism (architectural decision)

`RemoteProgressSyncPort` in `core.ports` has no delete methods and **MUST NOT be modified**. The cache service needs a separate dependency for remote deletes.

**Chosen approach**: Inject `DatabaseService` (or a protocol wrapping its `delete_word`/`delete_words` methods) as an optional constructor parameter `remote_db: DatabaseService | None`. When `None` (default), construct one using the same user/language config. This mirrors the existing pattern where `ExerciseProgressStore` is constructed as the default `remote_progress` when none is injected.

A minimal `RemoteDeletePort` protocol will be defined inside `database_cache` to decouple from the concrete `DatabaseService` class in tests while keeping the same call-through for production.

## Scope

### In

- FR-7: `list_personal_words()` from local SQLite (uses cached word pairs + scores + added_at)
- FR-8: `get_progress_summary()` computed from the same local record set (DEC-7)
- FR-9: `delete_word()` / `delete_words()` — remote-first, then local prune (DEC-6, FM-5, BR-6)
- FR-10: `refresh()` persists `added_at` from `EnrichedWordPairSnapshot` into SQLite
- File decomposition of `service.py` (190 lines) and `local_store.py` (196 lines) to stay under 200 lines
- Schema migration: add `added_at TEXT` column to `cached_word_pairs` DDL

### Out

- Modifying `core.ports.RemoteProgressSyncPort`
- Modifying any `database` package code
- Multi-device cache coordination
- Untranslated word support (A-3 assumption stands)

## Inputs (contracts)

- Requirements: `docs/module-spec.md` (FR-7 through FR-10, DEC-6, DEC-7, BR-6, FM-5, CR-3)
- Module spec: `docs/module-spec.md`
- Dependency models: `database.models.PersonalWord`, `database.models.EnrichedWordPairSnapshot`, `database.models.ExerciseProgressSummary`
- Dependency helpers: `database._progress_helpers.compute_progress_summary()`
- Core port: `core.ports.RemoteProgressSyncPort` (read-only)

## Change digest

- **Requirement deltas**:
  - FR-7: New `list_personal_words()` on `DatabaseCacheService`
  - FR-8: New `get_progress_summary()` on `DatabaseCacheService`
  - FR-9: New `delete_word()` / `delete_words()` on `DatabaseCacheService`
  - FR-10: `refresh()` must persist `added_at` from `EnrichedWordPairSnapshot`

## File Decomposition Strategy

### `service.py` (190/200 lines) — CRITICAL

Current state: 190 lines. Adding `list_personal_words()`, `get_progress_summary()`, `delete_word()`, `delete_words()` plus new constructor params would push to ~240+ lines.

**Strategy**: Extract `_row_to_word_pair()`, `_parse_dt()`, and the two background task methods into a new `_service_helpers.py` file (~30–35 lines). This frees ~35 lines in `service.py`, bringing it to ~155 lines with room for the new methods (~40 lines total for the 4 new methods + constructor changes).

### `local_store.py` (196/200 lines) — CRITICAL

Current state: 196 lines. Adding `delete_word_pairs()`, `delete_scores()`, `delete_pending_events()`, and `get_cached_word_pairs_with_added_at()` would push to ~250+ lines.

**Strategy**: Extract the lower-level utility methods (`_fetch_all`, `_exec_commit`, `open`, `close`, `_conn` property, `_now`) into a new `_local_store_base.py` file (~45 lines). `LocalStore` inherits or composes from it. This frees ~45 lines, leaving `local_store.py` at ~155 lines with room for the new delete and query methods.

### `_local_store_queries.py` (58 lines) — grows modestly

New SQL constants for delete operations and `added_at`-aware insert/select. Expected final: ~75–80 lines.

## Task list (dependency-aware)

- **T1:** `TASK_decompose_files.md` (depends: —) — Decompose `service.py` and `local_store.py` to stay under 200-line limit
- **T2:** `TASK_schema_and_refresh_added_at.md` (depends: T1) — Add `added_at` to DDL, persist it in refresh, update tuple handling
- **T3:** `TASK_list_personal_words.md` (depends: T2) — Implement `list_personal_words()` local read API
- **T4:** `TASK_progress_summary.md` (depends: T3) — Implement `get_progress_summary()` from cached data
- **T5:** `TASK_delete_apis.md` (depends: T2) (parallel: yes, with T3+T4) — Implement `delete_word()` / `delete_words()` with remote-first + local prune
- **T6:** `TASK_e2e_tests.md` (depends: T3, T4, T5) — E2E tests for personal vocab, progress summary, and delete

## Dependency graph (DAG)

```
T1 → T2 → T3 → T4 → T6
           ↘          ↗
            T5 ------
```

- T1 (decompose) must come first — all subsequent tasks add code to the decomposed files
- T2 (schema + refresh) depends on T1 — changes DDL and refresh in the decomposed `local_store.py`
- T3 (list_personal_words) depends on T2 — reads `added_at` from the schema T2 creates
- T4 (progress_summary) depends on T3 — DEC-7 requires using the same cached record set
- T5 (delete) depends on T2 — deletes from the schema T2 creates; parallel with T3/T4 but serialized for safety due to shared files
- T6 (e2e) depends on T3, T4, T5 — end-to-end validation of all new features

## Execution plan

### Critical path

T1 → T2 → T3 → T4 → T6

### Parallel tracks (lanes)

- **Lane A (main)**: T1 → T2 → T3 → T4 → T6
- **Lane B (delete)**: T5 (after T2, could parallelize with T3/T4 in theory, but serialized due to shared file contention in `service.py` and `local_store.py`)

**Decision**: Serialize T5 after T2 and before T6. T3, T4, and T5 all modify `service.py` and `local_store.py`, so parallel execution risks merge conflicts. Order: T3 → T4 → T5 gives cleanest incremental builds, but T5 can also run after T2 if T3/T4 are blocked.

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development uses testing/development databases.
- **Shared resource isolation**: SQLite cache files use `tmp_path` in tests. E2E tests connect to the testing Neon database (identified by `DATABASE_URL` env var in the test environment) and use advisory locks + table resets to avoid collision. The production bot runs from a separate directory with its own `DATABASE_URL`.
- **Schema change**: The `added_at TEXT` column addition to `cached_word_pairs` DDL uses `CREATE TABLE IF NOT EXISTS`. Existing production SQLite caches will be rebuilt on next `refresh()` call (the table is dropped and recreated during refresh). No migration needed — the cache is ephemeral.

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- Unit tests pass: `uv run pytest tests/unit/database_cache/ -x -v`
- Integration tests pass: `uv run pytest tests/integration/database_cache/ -x -v`
- E2E tests pass: `uv run pytest tests/e2e/database_cache/ -x -v`
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches module spec exactly (FR-7 through FR-10)
- All files stay under 200 lines (enforced by pylint)
- Zero legacy tolerance (dead code removed; codebase in sync with docs)
- No errors are silenced (no swallowed exceptions)
- Requirements/architecture docs unchanged
- Production database untouched; all development against testing DB only
- jscpd zero-tolerance: no duplicated fixture/setup patterns across test files

## Risks + mitigations

- **Risk**: `service.py` (190 lines) and `local_store.py` (196 lines) will exceed 200 lines if code is added before decomposition.
  - **Mitigation**: T1 (decompose) is the mandatory first task. All subsequent tasks work with the decomposed files. Each task re-checks line counts as a verification gate.

- **Risk**: `EnrichedWordPairSnapshot` has `added_at: datetime` but current `rebuild_snapshot()` uses 6-element tuples. Growing to 7 elements may break existing callers.
  - **Mitigation**: T2 updates the tuple format and all call sites in `sync.py` and `local_store.py` atomically. Existing tests are updated in the same task.

- **Risk**: The `RemoteDeletePort` protocol introduces a new dependency injection point in the constructor. Existing callers that don't need delete won't break (default construction).
  - **Mitigation**: The parameter is optional with a default factory (same pattern as `remote_progress`).

- **Risk**: `compute_progress_summary()` from `database._progress_helpers` expects rows with `source_id` key, but cached rows use `source_word_id`.
  - **Mitigation**: T4 implements a local version of the summary math that works with the cached row shape, or transforms rows before calling the helper. The math is simple enough (~10 lines) that a local implementation avoids fragile coupling to `database` internal row key names.

- **Risk**: Delete prunes local state but a subsequent `refresh()` could re-add the word if it hasn't been deleted remotely yet (race condition).
  - **Mitigation**: DEC-6 mandates remote-first delete. By the time local state is pruned, the remote has already deleted the word. A subsequent refresh from remote will not contain it.

- **Risk**: jscpd may flag duplicate `MockProgressStore` classes across unit and integration conftest files.
  - **Mitigation**: Assess during T1. If duplication exists, extract to a shared test helper module. The integration `MockProgressStore` has additional `apply_errors_by_call` that the unit version doesn't, so they are functionally distinct, but monitor.

## Sources used

- Requirements: `docs/module-spec.md`
- Module spec: `docs/module-spec.md`
- Code read (for scoping only):
  - `src/nl_processing/database_cache/service.py`
  - `src/nl_processing/database_cache/sync.py`
  - `src/nl_processing/database_cache/local_store.py`
  - `src/nl_processing/database_cache/_local_store_queries.py`
  - `src/nl_processing/database_cache/models.py`
  - `src/nl_processing/database_cache/exceptions.py`
  - `src/nl_processing/database_cache/logging.py`
  - `tests/unit/database_cache/` (all files)
  - `tests/integration/database_cache/` (all files)
  - `tests/e2e/database_cache/` (all files)
  - `../core/src/nl_processing/core/ports.py`
  - `../core/src/nl_processing/core/models.py`
  - `../database/src/nl_processing/database/models.py`
  - `../database/src/nl_processing/database/exceptions.py`
  - `../database/src/nl_processing/database/service.py`
  - `../database/src/nl_processing/database/exercise_progress.py`
  - `../database/src/nl_processing/database/_progress_helpers.py`

## Contract summary

### What (requirements)

- FR-7: `list_personal_words()` — local personal-vocabulary read returning `PersonalWord` objects with `added_at` and scores
- FR-8: `get_progress_summary()` — per-exercise progress stats from the same cached record set
- FR-9: `delete_word()` / `delete_words()` — remote-first delete then local prune (rows + scores + pending events)
- FR-10: `refresh()` persists `added_at` from `EnrichedWordPairSnapshot` into `cached_word_pairs`

### How (architecture)

- SQLite schema grows: `cached_word_pairs` gets `added_at TEXT` column
- `CacheSyncer.refresh()` extracts `added_at` from `EnrichedWordPairSnapshot` objects (7-element tuples)
- New `RemoteDeletePort` protocol inside `database_cache` for remote delete injection
- `DatabaseService` is the default concrete delete implementation (constructed like `ExerciseProgressStore`)
- Progress summary uses local math over cached scores (DEC-7)
- `service.py` and `local_store.py` decomposed before adding new code

## Impact inventory (implementation-facing)

- **Module**: `database_cache` at `src/nl_processing/database_cache/`
- **Interfaces**: `list_personal_words()`, `get_progress_summary()`, `delete_word()`, `delete_words()` added to `DatabaseCacheService`
- **Data model**: `cached_word_pairs` table gains `added_at TEXT` column; `rebuild_snapshot()` tuple grows from 6 to 7 elements
- **External services**: `DatabaseService.delete_word()` / `delete_words()` called for remote-first delete; `ExerciseProgressStore.export_remote_snapshot()` now returns `EnrichedWordPairSnapshot` with `added_at`
- **Test directory**: `tests/unit/database_cache/`, `tests/integration/database_cache/`, `tests/e2e/database_cache/`
