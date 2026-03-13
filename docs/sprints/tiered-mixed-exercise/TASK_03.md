---
Task ID: T3
Title: Implement `TieredExerciseCacheService` in `database_cache`
Sprint: `2026-03-14_tiered-mixed-exercise`
Module: database_cache
Depends on: T2
Parallelizable: no (depends on T2; T4 can run in parallel)
---

## Goal / value

After this task, the `database_cache` package exposes a fully tested `TieredExerciseCacheService` that manages a local SQLite tiered schema (snapshot rows, repeat-state mirror, tiered outbox), supports init/refresh/flush lifecycle, serves tiered candidate reads and mixed progress summaries entirely from local state after initialization, and syncs back to the remote `TieredExerciseProgressStore` via the `RemoteTieredSyncPort` contract. All existing `DatabaseCacheService` behavior remains untouched.

## Context (contract mapping)

- Spec: `packages/database_cache/docs/module-spec.md` Section 5 (TFR-DC-1..7, TBR-DC-1..5, TIF-DC-1..4, TDEC-DC-1..3, TAC-DC-1..4)
- Core tiered models from T1: `TieredCandidate`, `TieredProgressSummary`, `TieredSnapshotEntry`
- Core tiered ports from T1: `TieredCandidateProvider`, `RemoteTieredSyncPort`
- Remote tiered store from T2: `TieredExerciseProgressStore`
- Existing cache patterns: `service.py`, `local_store.py`, `sync.py`, `_local_store_queries.py`, `_local_store_base.py`

## Preconditions

- T1 completed: `core` has tiered DTOs and ports.
- T2 completed: `database` has `TieredExerciseProgressStore` implementing `RemoteTieredSyncPort`.
- `make -C packages/database_cache check` passes before starting.

## Non-goals

- Modifying existing `DatabaseCacheService`, `LocalStore`, `CacheSyncer`, or `DetailedWordCacheService`.
- Sharing internal SQLite tables with the existing cache schema (tiered cache is isolated per TDEC-DC-1).
- Implementing sampling logic (that's T4).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**

- `packages/database_cache/src/nl_processing/database_cache/` -- add tiered cache service, local store, syncer, queries
- `packages/database_cache/tests/` -- add tiered tests

**FORBIDDEN -- this task must NEVER touch:**

- `packages/core/`, `packages/database/`, `packages/sampling/`
- Existing `service.py`, `local_store.py`, `sync.py`, `_local_store_base.py`, `_local_store_queries.py`, `models.py`, `ports.py`, `exceptions.py`
- `docs/`, `Makefile`, `pyproject.toml`, `ruff.toml`

**Test scope:**

- Tests go in: `packages/database_cache/tests/unit/database_cache/` and `packages/database_cache/tests/integration/database_cache/`
- Test command: `make -C packages/database_cache check`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- NEW: `packages/database_cache/src/nl_processing/database_cache/_tiered_queries.py` -- DDL and DML for tiered local tables
- NEW: `packages/database_cache/src/nl_processing/database_cache/_tiered_local_store.py` -- SQLite data access for tiered snapshot, repeat-state, and outbox
- NEW: `packages/database_cache/src/nl_processing/database_cache/tiered_sync.py` -- refresh/flush orchestration for tiered cache
- NEW: `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py` -- `TieredExerciseCacheService` public API
- NEW: `packages/database_cache/src/nl_processing/database_cache/_tiered_helpers.py` -- tiered-specific helper functions (repeat-state transition, progress computation from local rows)
- NEW: `packages/database_cache/tests/unit/database_cache/test_tiered_local_store.py` -- local store unit tests
- NEW: `packages/database_cache/tests/unit/database_cache/test_tiered_transition.py` -- local transition matrix tests (must match database's matrix exactly)
- NEW: `packages/database_cache/tests/unit/database_cache/test_tiered_cache.py` -- service-level unit tests with mock remote
- NEW: `packages/database_cache/tests/integration/database_cache/test_tiered_lifecycle.py` -- integration tests with real remote

## Dependencies and sequencing notes

- Depends on T2 because the tiered cache needs `TieredExerciseProgressStore` (or any `RemoteTieredSyncPort` implementor) for remote sync.
- T4 (sampling) can run in parallel since it only needs T1's `TieredCandidateProvider` protocol.

## Third-party / library research (mandatory for any external dependency)

No new third-party dependencies. Uses existing:

- **aiosqlite** (already used in `_local_store_base.py` for async SQLite access)
  - Documentation: https://aiosqlite.omnilib.dev/en/stable/
  - Key pattern: `async with db.execute(sql, params)` for queries, `await db.commit()` for writes.

## Implementation steps (developer-facing)

1. **Create `packages/database_cache/src/nl_processing/database_cache/_tiered_queries.py`** with DDL and DML constants:
   - `DDL_TIERED_SNAPSHOT` -- `CREATE TABLE IF NOT EXISTS tiered_cached_word_pairs (source_word_id INTEGER NOT NULL, source_normalized_form TEXT NOT NULL, source_word_type TEXT NOT NULL, target_word_id INTEGER NOT NULL, target_normalized_form TEXT NOT NULL, target_word_type TEXT NOT NULL, PRIMARY KEY (source_word_id))`.
   - `DDL_TIERED_SCORES` -- `CREATE TABLE IF NOT EXISTS tiered_cached_scores (source_word_id INTEGER NOT NULL, exercise_type TEXT NOT NULL, score INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL, PRIMARY KEY (source_word_id, exercise_type))`.
   - `DDL_TIERED_REPEAT_STATE` -- `CREATE TABLE IF NOT EXISTS tiered_repeat_state (mode_slug TEXT NOT NULL, source_word_id INTEGER NOT NULL, activated_at TEXT NOT NULL, PRIMARY KEY (mode_slug, source_word_id))`.
   - `DDL_TIERED_PENDING_EVENTS` -- `CREATE TABLE IF NOT EXISTS tiered_pending_events (event_id TEXT PRIMARY KEY, mode_slug TEXT NOT NULL, source_word_id INTEGER NOT NULL, exercise_type TEXT NOT NULL, delta INTEGER NOT NULL, created_at TEXT NOT NULL, flushed_at TEXT, last_error TEXT)`.
   - `DDL_TIERED_METADATA` -- `CREATE TABLE IF NOT EXISTS tiered_cache_metadata (id INTEGER PRIMARY KEY DEFAULT 1, mode_slug TEXT NOT NULL, exercise_types TEXT NOT NULL, schema_version INTEGER NOT NULL DEFAULT 1, last_refresh_started_at TEXT, last_refresh_completed_at TEXT, last_flush_completed_at TEXT, last_error TEXT)`.
   - `ALL_TIERED_DDL` -- list of all DDL statements above.
   - DML constants: `UPSERT_TIERED_SCORE`, `INSERT_TIERED_WORD_PAIR`, `INSERT_TIERED_PENDING_EVENT`, `INSERT_TIERED_REPEAT_STATE`, `DELETE_TIERED_REPEAT_STATE`.

2. **Create `packages/database_cache/src/nl_processing/database_cache/_tiered_local_store.py`** extending `LocalStoreBase`:
   - `TieredLocalStore(LocalStoreBase)` with methods:
     - `async def open(self)` -- open connection, execute `ALL_TIERED_DDL`.
     - `async def get_tiered_candidates(self, mode_slug, exercise_types) -> list[dict]` -- join snapshot + scores + repeat-state.
     - `async def get_tiered_pending_events(self) -> list[dict]` -- unflushed tiered events.
     - `async def get_tiered_pending_event_count(self) -> int`.
     - `async def record_tiered_score_and_event(self, mode_slug, source_word_id, exercise_type, delta, event_id, next_in_repeat) -> None` -- atomic: upsert score, update repeat-state, insert pending event, commit.
     - `async def rebuild_tiered_snapshot(self, word_pairs, scores, repeat_states) -> None` -- atomic replace of snapshot + scores + repeat-state, then reapply pending events.
     - `async def mark_tiered_event_flushed(self, event_id) -> None`.
     - `async def mark_tiered_event_failed(self, event_id, error) -> None`.
     - `async def ensure_tiered_metadata(self, mode_slug, exercise_types) -> None`.
     - `async def get_tiered_metadata(self) -> dict | None`.
     - `async def has_tiered_snapshot(self) -> bool`.
     - `async def update_tiered_metadata(self, **fields) -> None`.

3. **Create `packages/database_cache/src/nl_processing/database_cache/_tiered_helpers.py`**:
   - `compute_next_repeat_state(current_in_repeat, delta, scores_after_update, exercise_types) -> bool` -- same pure function as in `database/_tiered_helpers.py`. Must produce identical results. Reimplement locally (cannot import from `database` internal module) but test with identical test cases.
   - `validate_repeat_state_integrity(in_repeat, scores, exercise_types) -> None` -- same validation.
   - `compute_local_tiered_progress(rows, exercise_types) -> TieredProgressSummary` -- compute from local row dicts.

4. **Create `packages/database_cache/src/nl_processing/database_cache/tiered_sync.py`** following the `sync.py` pattern:
   - `TieredCacheSyncer` with `__init__(self, local_store: TieredLocalStore, remote: RemoteTieredSyncPort)`.
   - `async def refresh(self)` -- pull `export_tiered_snapshot()` from remote, rebuild local snapshot, reapply pending events.
   - `async def flush(self, *, skip_if_running=False)` -- push pending tiered events to remote via `apply_tiered_result()`, mark flushed.

5. **Create `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`** -- `TieredExerciseCacheService`:
   - Constructor: `__init__(self, *, user_id, source_language, target_language, mode_slug, exercise_types, cache_ttl, remote_tiered_progress=None, local_store=None, cache_dir=None)`. Validates `mode_slug`, `exercise_types`.
   - `async def init(self) -> CacheStatus` -- open local store, bootstrap or refresh, return status. Follow the same pattern as existing `DatabaseCacheService.init()`. If no remote is injected, construct `TieredExerciseProgressStore` as default.
   - `async def get_tiered_candidates(self) -> list[TieredCandidate]` -- read from local store, validate repeat-state integrity, return `TieredCandidate` list.
   - `async def get_tiered_progress_summary(self) -> TieredProgressSummary` -- compute from local candidates.
   - `async def record_tiered_result(self, *, source_word_id, exercise_type, delta) -> None` -- validate inputs, compute current scores, derive next repeat-state, write locally (score + repeat-state + pending event), trigger background flush.
   - `async def refresh(self) -> None`, `async def flush(self) -> None`, `async def get_status(self) -> CacheStatus`.

6. **Create unit tests:**
   - `test_tiered_transition.py`: Identical transition matrix tests as in `database/test_tiered_transition.py`. This is the shared parity test per TRISK-DC-2.
   - `test_tiered_local_store.py`: Test SQLite operations -- schema creation, snapshot rebuild, score/event recording, repeat-state updates.
   - `test_tiered_cache.py`: Test service behavior with a mock `RemoteTieredSyncPort` -- init, candidate reads, result recording, progress summary.

7. **Create integration tests:**
   - `test_tiered_lifecycle.py`: Test full lifecycle with a real remote `TieredExerciseProgressStore` -- init from remote, local reads, record result, flush to remote, refresh from remote, verify consistency.

8. **Run `make -C packages/database_cache check`** and verify all tests pass.

## Production safety constraints (mandatory)

- **Database operations**: Integration tests that touch remote use the Doppler-managed testing `DATABASE_URL`. Local tests use temporary SQLite files.
- Cache files use per-user-per-mode file paths -- no overlap with production.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow `service.py`, `local_store.py`, `sync.py` patterns exactly. The tiered cache is a structural parallel.
- **Correct libraries only**: `aiosqlite` (already in lockfile).
- **Correct file locations**: New files follow existing `_local_store_*.py`, `sync.py`, `service.py` naming patterns.
- **No regressions**: Existing `DatabaseCacheService` tests must pass unchanged (TAC-DC-1).

## Error handling + correctness rules (mandatory)

- Wrap `sqlite3.Error` as `CacheStorageError` (existing pattern).
- `validate_repeat_state_integrity` must raise `ValueError` -- never silently normalize (TBR-DC-4).
- Unknown `exercise_type` in `record_tiered_result` must raise `ValueError`.
- `delta` not in `(1, -1)` must raise `ValueError`.
- `CacheNotReadyError` if methods are called before `init()`.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove. Purely additive.
- Do not create placeholder methods.

## Acceptance criteria (testable)

1. `TieredExerciseCacheService` can be constructed and initialized (TAC-DC-1 preserved).
2. After init/refresh, tiered candidate reads come entirely from local SQLite -- no remote call (TFR-DC-2, TAC-DC-2).
3. `record_tiered_result()` updates local score, local repeat-state, and pending event atomically before returning (TFR-DC-4, TAC-DC-3).
4. `refresh()` rebuilds local snapshot from remote without losing unflushed local results (TFR-DC-5, TAC-DC-4).
5. `flush()` replays pending tiered events to remote idempotently.
6. Mixed progress summary counts a word as positive only when all participating scores are `> 0` (TFR-DC-6).
7. Local repeat-state transitions match remote transitions exactly (TBR-DC-1 -- verified by identical unit test cases).
8. Existing `DatabaseCacheService` tests pass unchanged (TFR-DC-7).
9. `make -C packages/database_cache check` passes.

## Verification / quality gates

- [ ] Unit tests for local transition matrix (identical cases to database's matrix)
- [ ] Unit tests for local store SQLite operations
- [ ] Unit tests for service with mock remote
- [ ] Integration test for full lifecycle with real remote
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] All files under 200 lines
- [ ] Negative-path tests: CacheNotReadyError, invalid repeat-state, unknown exercise_type

## Edge cases

- Init with no words in remote: should produce empty snapshot, zero progress.
- Pending events survive refresh: after rebuild, pending events are reapplied.
- Concurrent flush: second flush skips if first is running.
- Mode slug mismatch: if stored metadata has a different mode_slug, refresh must be triggered.
- Cache file already exists from a previous session: `open()` must be idempotent.

## Notes / risks

- **Risk**: The `_tiered_helpers.py` in `database_cache` reimplements the same transition logic as `database/_tiered_helpers.py`, creating a duplication risk.
  - **Mitigation**: This is intentional per module isolation rules (cache cannot import from database internals). The parity is enforced by running identical test cases in both modules. If the specs change, both test files must be updated in the same sprint.

- **Risk**: `_local_store_base.py` is currently 72 lines, so `TieredLocalStore` can safely inherit from it without file-size issues.
  - **Mitigation**: Keep `_tiered_local_store.py` focused on tiered operations only. If it grows too large, split read vs write methods into separate files.
