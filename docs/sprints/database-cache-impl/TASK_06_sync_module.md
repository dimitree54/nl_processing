---
Task ID: T6
Title: Create `sync.py` — refresh and flush orchestration
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T5
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Create `sync.py` — the orchestration layer for refresh (snapshot download + local rebuild) and flush (pending event replay to remote). This file coordinates between `LocalStore` (local SQLite) and `ExerciseProgressStore` (remote Neon), enforcing concurrency guards (one refresh at a time, one flush at a time).

## Context (contract mapping)

- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Refresh" lifecycle (steps 1–5), "Flush" lifecycle (steps 1–4), "Module Internal Structure" lists `sync.py`
- Requirements:
  - FR19: `refresh()` fetches translated word pairs and scores from `database`
  - FR20: Refresh rebuilds local snapshot atomically
  - FR21: During refresh, existing snapshot stays available
  - FR22: Pending outbox events reapplied after refresh
  - FR23: `flush()` replays pending events to remote
  - FR24: Failed flushes remain pending for retry
  - FR25: Only one refresh at a time
  - FR26: Only one flush at a time

## Preconditions

- T5 complete (`local_store.py` provides `LocalStore` with `rebuild_snapshot()`, `get_pending_events()`, `mark_event_flushed()`, `mark_event_failed()`, `update_metadata()`)

## Non-goals

- Managing the service-level public API (that's `service.py`, T7)
- Writing tests (T9)
- TTL/staleness decisions (that's `service.py`, T7)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database_cache/sync.py` — create this file

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/database/` — consumed, not modified
- Any other module's code or tests

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes

## Touched surface (expected files / modules)

- `nl_processing/database_cache/sync.py` (new file)

## Dependencies and sequencing notes

- Depends on T5 (local_store) — uses `LocalStore` methods
- T7 (service) depends on this task
- On the critical path

## Third-party / library research (mandatory for any external dependency)

- **`asyncio` locks**: https://docs.python.org/3.12/library/asyncio-sync.html#asyncio.Lock
  - `asyncio.Lock()` — used for concurrency guards (one refresh, one flush at a time).
  - Pattern: `async with self._refresh_lock: ...`
  - Non-reentrant — if the same coroutine tries to acquire it twice, it will deadlock. This is fine because refresh/flush are top-level operations.
- **`ExerciseProgressStore` API** (from `nl_processing/database/exercise_progress.py`):
  - `export_remote_snapshot() -> list[ScoredWordPair]` — returns word pairs + scores
  - `apply_score_delta(event_id, source_word_id, exercise_type, delta)` — idempotent replay
- **`ScoredWordPair` model** (from `nl_processing/database/models.py`):
  - `.pair: WordPair` with `.source: Word` and `.target: Word`
  - `.scores: dict[str, int]`
  - `.source_word_id: int`

## Implementation steps (developer-facing)

1. Create `nl_processing/database_cache/sync.py`.

2. Define a `CacheSyncer` class:

   **Constructor**: accepts `local_store: LocalStore`, `progress_store: ExerciseProgressStore`, stores them. Creates two `asyncio.Lock` instances: `_refresh_lock` and `_flush_lock`.

   **`async refresh() -> None`**:
   - Acquire `_refresh_lock` (non-blocking: if already running, raise `CacheSyncError` or silently skip — architecture says "only one refresh at a time", so use `Lock.acquire()` with a check).
   - Implementation: Use `if self._refresh_lock.locked(): return` to silently skip if already in progress (FR25).
   - Update metadata: `last_refresh_started_at = now`.
   - Call `self._progress_store.export_remote_snapshot()` to fetch `list[ScoredWordPair]`.
   - Transform the snapshot into the format expected by `LocalStore.rebuild_snapshot()`:
     - Word pairs: list of tuples `(source_word_id, source_normalized_form, source_word_type, target_word_id, target_normalized_form, target_word_type)`
     - Scores: dict mapping `(source_word_id, exercise_type)` to score value
   - Call `self._local_store.rebuild_snapshot(word_pairs, scores)` — this atomically replaces data and reapplies pending events.
   - Update metadata: `last_refresh_completed_at = now`.
   - On error: log the error, update metadata `last_error`, re-raise as `CacheSyncError`.

   **`async flush() -> None`**:
   - Acquire `_flush_lock` (same pattern: skip if already in progress).
   - Get pending events from `self._local_store.get_pending_events()`.
   - For each event (oldest first):
     - Call `self._progress_store.apply_score_delta(event_id=..., source_word_id=..., exercise_type=..., delta=...)`.
     - On success: call `self._local_store.mark_event_flushed(event_id)`.
     - On failure: call `self._local_store.mark_event_failed(event_id, str(error))`, log the error, continue to next event (FR24).
   - Update metadata: `last_flush_completed_at = now`.
   - On catastrophic error (e.g., all events fail): update metadata `last_error`, raise `CacheSyncError`.

3. Ensure `_refresh_lock` and `_flush_lock` are always released (use `async with` or try/finally).

4. Keep file ≤ 200 lines.

## Production safety constraints (mandatory)

- **Database operations**: `refresh()` reads from remote Neon (via `ExerciseProgressStore`), writes to local SQLite only. `flush()` writes to remote Neon (via `apply_score_delta`) — this uses the `dev` environment in tests, never production.
- **Resource isolation**: Remote operations go through `ExerciseProgressStore` which reads `DATABASE_URL` from env. In unit/integration tests, the progress store is mocked. In E2E tests, `doppler run --` provides the dev DATABASE_URL.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses `LocalStore` methods from T5 — no duplication.
- **Correct libraries only**: stdlib `asyncio.Lock`, project-internal `LocalStore` and `ExerciseProgressStore`.
- **Correct file locations**: `nl_processing/database_cache/sync.py` per architecture spec.
- **No regressions**: New file, no existing code affected.

## Error handling + correctness rules (mandatory)

- **Refresh errors**: Caught, logged, stored in metadata. Re-raised as `CacheSyncError`. Existing snapshot remains usable (FR21).
- **Flush errors per event**: Caught per-event, logged, event marked as failed with error message. Other events continue processing (FR24).
- **Lock contention**: If refresh/flush is already running, silently skip (do not queue or block indefinitely).
- Never swallow errors silently — all errors are logged and stored in metadata.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove.

## Acceptance criteria (testable)

1. File `nl_processing/database_cache/sync.py` exists.
2. `CacheSyncer` class is defined with `refresh()` and `flush()` methods.
3. `refresh()` calls `export_remote_snapshot()`, transforms data, calls `rebuild_snapshot()`, updates metadata timestamps.
4. `flush()` iterates pending events, calls `apply_score_delta()` per event, marks each as flushed or failed.
5. Only one refresh can run at a time; concurrent calls are silently skipped.
6. Only one flush can run at a time; concurrent calls are silently skipped.
7. Errors are wrapped in `CacheSyncError` and logged.
8. File is ≤ 200 lines.
9. `make check` passes.

## Verification / quality gates

- [ ] File exists with correct content
- [ ] `make check` passes
- [ ] No new warnings introduced

## Edge cases

- `export_remote_snapshot()` returns empty list (user has no words) — `rebuild_snapshot()` clears all local data, which is correct.
- `flush()` with no pending events — no-op, just updates `last_flush_completed_at`.
- `apply_score_delta()` raises for one event but succeeds for others — failed event stays pending, others marked flushed.
- `refresh()` called while `flush()` is running — both can proceed independently (separate locks).

## Notes / risks

- **Risk**: `refresh()` and `flush()` racing could cause inconsistency (refresh overwrites scores that flush just sent).
  - **Mitigation**: Architecture addresses this: `rebuild_snapshot()` reapplies pending events after overwriting. Events are only marked flushed after successful remote apply, so they survive a refresh.
