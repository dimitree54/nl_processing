---
Sprint ID: `2026-03-08_auto-flush`
Sprint Goal: `Every record_exercise_result() call automatically triggers a fire-and-forget background flush`
Sprint Type: `module`
Module: `database_cache`
Status: `planning`
Owners: `Developer`
---

## Goal

After this sprint, `record_exercise_result()` automatically starts a background flush (`asyncio.create_task`) after each local write commits. `flush()` remains available as a public method for explicit use. All existing tests continue to pass; new tests verify the auto-flush behaviour at unit, integration, and E2E levels.

## Module Scope

### What this sprint implements
- Module: `database_cache`
- Architecture spec: `nl_processing/database_cache/docs/architecture_database_cache.md`
- PRD: `nl_processing/database_cache/docs/prd_database_cache.md`

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `nl_processing/database_cache/service.py` — add `_background_flush()` and the `create_task` call
- `tests/unit/database_cache/test_service.py` — add unit tests for auto-flush
- `tests/integration/database_cache/test_flush_retry.py` — add integration test for auto-flush
- `tests/e2e/database_cache/test_full_loop.py` — add E2E test for auto-flush

**FORBIDDEN — this sprint must NEVER touch:**
- Any other module's code or tests
- `nl_processing/database_cache/sync.py` — flush lock already handles concurrent calls; no changes needed
- `nl_processing/database_cache/local_store.py` — no changes needed
- Any bot code, handlers, routing, or state management
- `docs/requirements/`, `docs/architecture/`, or any docs outside this sprint folder

### Test Scope
- **Test directories**: `tests/unit/database_cache/`, `tests/integration/database_cache/`, `tests/e2e/database_cache/`
- **Test commands**:
  - `uv run pytest tests/unit/database_cache/ -x -v`
  - `doppler run -- uv run pytest tests/integration/database_cache/ -x -v`
  - `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v`
- **Quality gate**: `make check` (runs all test tiers + linters)

## Interface Contract

### Public interface — no changes

The public interface of `DatabaseCacheService` does not change. `record_exercise_result()` keeps the same signature and return type (`None`). `flush()` remains public. The only change is internal: `record_exercise_result()` now fires a background task after the local write.

### Internal addition

```python
async def _background_flush(self) -> None:
    """Fire-and-forget flush wrapper with exception logging."""
    try:
        assert self._syncer is not None
        await self._syncer.flush()
    except Exception:
        _log.exception("background flush failed")
```

Called via `asyncio.create_task(self._background_flush())` at the end of `record_exercise_result()`.

## Scope

### In
- Add `_background_flush()` method to `DatabaseCacheService`
- Add `asyncio.create_task(self._background_flush())` call at end of `record_exercise_result()`
- Unit test: verify `record_exercise_result()` creates a background flush task
- Integration test: verify auto-flush delivers events to mock remote after brief wait
- E2E test: verify auto-flush delivers events to real Neon after brief wait

### Out
- No changes to `CacheSyncer`, `LocalStore`, models, exceptions, or logging
- No changes to `flush()` public method behaviour
- No changes to `_background_refresh()` or `init()` behaviour
- No schema changes, no migration needed

## Inputs (contracts)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` — FR19, FR20, FR25
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Record Exercise Result" lifecycle, "Local Writes Use Transactional Outbox + Auto-Flush" decision
- Existing code: `nl_processing/database_cache/service.py` — `_background_refresh()` pattern to mirror

## Change digest

- **Requirement deltas**: FR19 and FR20 describe the auto-flush behaviour that is documented but not yet implemented in code. This sprint closes that gap.
- **Architecture deltas**: Architecture already specifies auto-flush (step 5 of "Record Exercise Result"). Code needs to match.

## Task list (dependency-aware)

- **T1:** `TASK_01_add_background_flush.md` (depends: —) (parallel: no) — Add `_background_flush()` and auto-flush trigger to `record_exercise_result()`
- **T2:** `TASK_02_unit_tests.md` (depends: T1) (parallel: yes, with T3) — Unit tests for auto-flush behaviour
- **T3:** `TASK_03_integration_tests.md` (depends: T1) (parallel: yes, with T2) — Integration test for auto-flush event delivery
- **T4:** `TASK_04_e2e_tests.md` (depends: T1) (parallel: yes, with T2, T3) — E2E test for auto-flush against real Neon

## Dependency graph (DAG)

- T1 → T2
- T1 → T3
- T1 → T4

## Execution plan

### Critical path
- T1 → T2 (or T3 or T4 — all are parallel after T1)

### Parallel tracks (lanes)
- **Lane A (foundation)**: T1
- **Lane B (tests — parallel after T1)**: T2, T3, T4

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. Unit and integration tests use in-memory or tmp-dir SQLite + mock remote. E2E tests use Doppler-managed test credentials pointing to a separate Neon test database.
- **Shared resource isolation**: Cache files use `tmp_path` pytest fixtures (system temp dir). No port conflicts — SQLite is file-based, no server process.
- **Migration deliverable**: N/A — no data model changes.

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- `make check` passes (unit + integration + E2E + linters + vulture + jscpd)
- Module isolation: no files outside the ALLOWED list were touched
- `service.py` remains at or below 200 lines
- Public interface unchanged — `record_exercise_result()` signature and `flush()` remain as-is
- Zero legacy tolerance: manual `flush()` calls in caller code are no longer *required* but the method is *preserved* for explicit use (no dead code)
- No errors are silenced — `_background_flush()` logs exceptions
- Production database untouched; all development against testing DB only

## Risks + mitigations

- **Risk**: `service.py` exceeds 200-line pylint limit after adding `_background_flush()`.
  - **Mitigation**: The method is 5 lines + 1 blank line = 6 lines. Current file is 177 lines. Adding the method + 1 `create_task` line = ~184 lines. Well within limit.

- **Risk**: Unit tests that call `record_exercise_result()` now spawn background tasks that may interfere with test isolation.
  - **Mitigation**: Tests must either (a) mock `asyncio.create_task` to prevent the background task, or (b) await the task / use `asyncio.sleep(0)` to let it complete. Existing tests use a mock remote that succeeds instantly, so option (b) is safe.

- **Risk**: E2E auto-flush test is flaky due to timing.
  - **Mitigation**: Use a bounded retry loop (e.g., poll `get_status().pending_events == 0` with short sleeps, max 5 seconds) rather than a fixed `asyncio.sleep`.

## Migration plan (if data model changes)

N/A — no data model changes.

## Rollback / recovery notes

- Revert the single `create_task` line and remove `_background_flush()` to restore manual-only flush behaviour. No data or schema impact.

## Task validation status

- Per-task validation order: `T1` → `T2` → `T3` → `T4`
- Validator: `task-checker`
- Outcome: `pending`

## Sources used

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` (FR14–FR20, FR25–FR28)
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` (lifecycle, auto-flush decision, test strategy)
- Code read (for scoping only):
  - `nl_processing/database_cache/service.py` (177 lines — `record_exercise_result()`, `_background_refresh()`)
  - `nl_processing/database_cache/sync.py` (77 lines — `CacheSyncer.flush()` lock guard)
  - `tests/unit/database_cache/test_service.py` (109 lines)
  - `tests/unit/database_cache/conftest.py` (100 lines)
  - `tests/integration/database_cache/test_flush_retry.py` (114 lines)
  - `tests/integration/database_cache/conftest.py` (74 lines)
  - `tests/e2e/database_cache/test_full_loop.py` (127 lines)
  - `tests/e2e/database_cache/conftest.py` (28 lines)
  - `Makefile` (10 lines — `make check` definition)

## Contract summary

### What (requirements)
- FR19: After a successful local write, `record_exercise_result()` automatically starts a background flush
- FR20: The background auto-flush must not block `record_exercise_result()`
- FR25: `flush()` is called automatically after each `record_exercise_result()` and is also available as a public method

### How (architecture)
- `record_exercise_result()` calls `asyncio.create_task(self._background_flush())` after the local transaction commits
- `_background_flush()` wraps `self._syncer.flush()` with exception logging (mirrors `_background_refresh()`)
- `CacheSyncer.flush()` already uses a lock guard that skips if locked — concurrent auto-flushes are safe

## Impact inventory (implementation-facing)

- **Module**: `database_cache` (`nl_processing/database_cache/`)
- **Interfaces**: No public interface changes
- **Data model**: No changes
- **External services**: No new services; existing `ExerciseProgressStore` integration unchanged
- **Test directories**: `tests/unit/database_cache/`, `tests/integration/database_cache/`, `tests/e2e/database_cache/`
