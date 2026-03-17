---
title: "packages/database_cache async lifecycle clean shutdown"
document_type: "task"
module: "packages/database_cache"
status: "planned"
---

# Task: Make `packages/database_cache` background lifecycle and shutdown clean

## Problem Statement

`packages/database_cache -> make check` is currently green, but the package still emits a reproducible warning that is not acceptable to leave behind:

- `PytestUnhandledThreadExceptionWarning`
- from the `aiosqlite` worker thread
- `RuntimeError: Event loop is closed`
- observed during `tests/unit/database_cache/test_service.py::test_record_exercise_result_triggers_background_flush`

The package spec already requires that public-service `close()` stops background work and releases owned resources before shutdown completes. The remaining warning means `database_cache` still has a package-owned async lifecycle / teardown gap around background flush or refresh work and local SQLite resource ownership.

This follow-up task is narrowly about fixing that shutdown cleanliness inside `packages/database_cache`. It is not a reopening of the already-completed downstream adaptation away from `database.testing`, and it must not modify `packages/database`.

## Goal

Make `database_cache` service-owned background work deterministic and fully drained before owned SQLite resources and the event loop are torn down, so that:

- background flush / refresh work does not outlive package-owned service shutdown,
- tests and fixtures use package-owned lifecycle correctly,
- `aiosqlite` does not try to talk back to a closed event loop during teardown,
- final validation is green with no reproducible `PytestUnhandledThreadExceptionWarning`.

## Read First

### Package docs and prior task context

- `README.md`
- `docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`
- `packages/database_cache/docs/tasks/baseline-repair-green-check.md`
- `packages/database/docs/module-spec.md` **for read-only context only**

### Primary source files

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/_task_manager.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_operations.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`

### Tests and fixtures directly relevant to the warning/lifecycle path

- `packages/database_cache/tests/unit/database_cache/test_service.py`
- `packages/database_cache/tests/unit/database_cache/conftest.py`
- `packages/database_cache/tests/unit/database_cache/test_sync.py`
- `packages/database_cache/tests/integration/database_cache/test_flush_retry.py`
- `packages/database_cache/tests/integration/database_cache/conftest.py`

## Current Code-State Findings To Preserve In The Plan

These findings are already established from repo inspection and should drive implementation decisions:

- `DatabaseCacheService.record_exercise_result()` writes locally, then schedules `background_flush(self._syncer)` through `BackgroundTaskManager`.
- `DatabaseCacheService.init()` can also schedule a background refresh path through `setup_cache_state(... task_manager ...)` when cache metadata is stale.
- `DatabaseCacheService.close()` already exists and currently awaits `self._task_manager.close()` before `self._local.close()`, so the contract is present but the remaining warning shows current behavior is still not clean enough in practice.
- `BackgroundTaskManager.create_task()` tracks tasks in a set and discards them on completion, but it does not currently expose task handles to callers/tests and does not explicitly guard against scheduling new work while shutdown is in progress.
- `LocalStoreBase.close()` simply awaits `aiosqlite.Connection.close()` and clears the connection reference. The `aiosqlite` docs state that `close()` completes queued queries/cursors and closes the connection; that only works cleanly if package-owned tasks using the connection are already finished or are being shut down in a controlled order.
- `test_record_exercise_result_triggers_background_flush` currently monkeypatches `asyncio.create_task` and immediately `coro.close()`s the created coroutine. That test shape bypasses normal service-owned task lifecycle and is a likely contributor to the warning surface.
- `test_auto_flush_delivers_events_after_record` currently uses `await asyncio.sleep(0)` to let the background task run, which is not an acceptable final synchronization mechanism for this fix.
- `tests/integration/database_cache/test_flush_retry.py::test_auto_flush_delivers_events_after_record` currently uses a timing sleep and then closes `svc._local` directly instead of closing the owning service. That bypasses the package's public lifecycle contract and should be corrected.
- `packages/database_cache/docs/module-spec.md` explicitly says that `close()` on the public service must release owned local resources and stop background work before shutdown completes. The fix must align code and tests with that documented behavior.

## Scope

### In Scope

- Fix `database_cache` background task ownership, shutdown ordering, and teardown determinism.
- Make service shutdown fully drain or cancel package-owned background refresh / flush work before SQLite closure completes.
- Refactor package-local tests/fixtures that currently bypass or mis-model the public service lifecycle for background flush behavior.
- Add or adjust regression coverage proving that auto-flush and service close behave cleanly without timing sleeps or post-loop worker-thread exceptions.
- End with full `packages/database_cache -> make check` green and no reproducible warning.

### Out of Scope

- Any change in `packages/database` or any other package.
- Reopening the completed downstream adaptation from removed `database.testing` helpers.
- Protocol redesign, new cache features, or broader architecture cleanup.
- Warning suppression, filterwarnings, xfail, skip, retry inflation, or sleep-based stabilization.
- Editing any docs outside `packages/database_cache/docs/tasks/`.

## Required Design Direction

Implementation must take this concrete direction rather than leaving choices open:

1. `DatabaseCacheService` remains the owner of all background refresh/flush work it starts.
2. Service shutdown must prevent package-owned background work from continuing to use `LocalStore` after shutdown begins.
3. Tests must validate behavior through the service/task-manager lifecycle, not by monkeypatching global task creation into half-closed coroutine objects or by closing `svc._local` directly.
4. Synchronization in tests must be based on observable completion/state, not incidental event-loop yields or arbitrary sleeps.
5. `packages/database` stays read-only; if root-cause analysis proves the warning requires upstream changes there, stop and escalate instead of crossing module boundaries.

## Relevant Skills

- No specialized implementation skill is required for the code change itself.
- Do **not** expand this into `feature-request`, `bug-report`, `set-up-database`, or `set-up-env-vars`; this is a narrow package-local lifecycle repair.
- The package/module context is already documented in `packages/database_cache/docs/module-spec.md`; treat that as the behavioral contract.

## Targeted API / Library Research Already Done

These external references are directly relevant and should be used during implementation.

### `asyncio.create_task` background-task ownership

Python docs explicitly recommend keeping a strong reference to fire-and-forget tasks and removing them when done:

```python
background_tasks = set()
task = asyncio.create_task(some_coro())
background_tasks.add(task)
task.add_done_callback(background_tasks.discard)
```

Source: Python `asyncio` docs, “Creating Tasks” — https://docs.python.org/3/library/asyncio-task.html

This matches the intent of `BackgroundTaskManager`; the remaining task is to make the package lifecycle deterministic at shutdown and to test it through that owned mechanism.

### Cancellation handling for owned tasks

Python docs state that cancelled tasks should use `try/finally` for cleanup and that `CancelledError` should generally be propagated after cleanup.

Source: Python `asyncio` docs, “Task Cancellation” — https://docs.python.org/3/library/asyncio-task.html

Apply this when tightening any package-owned background coroutine shutdown behavior.

### `aiosqlite.Connection.close()` semantics

`aiosqlite` documents:

```python
await conn.close()
```

`close()` “Complete[s] queued queries/cursors and close[s] the connection”, and the docs say to prefer `await close()` over `stop()`.

Source: aiosqlite API reference — https://aiosqlite.omnilib.dev/en/stable/api.html

This means the package must not let background tasks keep scheduling SQLite work while or after `close()` is running.

### Pytest unhandled thread exception warnings are bug signals

Pytest documents `PytestUnhandledThreadExceptionWarning` as reporting unhandled exceptions in threads and states these warnings are normally considered bugs.

Source: pytest docs, “Warning about unraisable exceptions and unhandled thread exceptions” — https://docs.pytest.org/en/stable/how-to/failures.html

Therefore the fix must remove the underlying lifecycle problem, not filter or suppress the warning.

## Expected File Scope For Implementation

Primary expected changes:

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/_task_manager.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_operations.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/tests/unit/database_cache/test_service.py`
- `packages/database_cache/tests/unit/database_cache/conftest.py`
- `packages/database_cache/tests/unit/database_cache/test_sync.py`
- `packages/database_cache/tests/integration/database_cache/test_flush_retry.py`
- any existing package-local fixture/helper file directly involved in background flush lifecycle

Not allowed:

- any file in `packages/database`
- any file outside `packages/database_cache`
- any docs file outside `packages/database_cache/docs/tasks/`

## Implementation Plan

1. Reproduce the warning with the narrowest package-local command that hits `tests/unit/database_cache/test_service.py::test_record_exercise_result_triggers_background_flush`, and keep that command as the regression reproducer.
2. Trace the exact service-owned lifecycle for both background paths:
   - `record_exercise_result()` -> `BackgroundTaskManager.create_task()` -> `background_flush()` -> `CacheSyncer.flush()` -> `LocalStore`
   - `init()` stale-cache path -> `BackgroundTaskManager.create_task()` -> `background_refresh()` -> `CacheSyncer.refresh()` -> `LocalStore`
3. Tighten `BackgroundTaskManager` so shutdown is explicit and deterministic:
   - track service-owned tasks robustly,
   - refuse or safely close newly submitted coroutines after shutdown starts,
   - provide a reliable way for tests to observe or await scheduled task completion without monkeypatching global `asyncio.create_task`.
4. Tighten `DatabaseCacheService` shutdown semantics so public `close()` is the only supported owner shutdown path and no service-owned task can continue using SQLite after close begins.
5. Make any background helper / sync coroutine paths cancellation-safe and cleanup-safe so task cancellation does not leave half-shutdown work still trying to use the connection.
6. Update package-local tests and fixtures to use the public lifecycle correctly:
   - remove the global `asyncio.create_task` monkeypatch pattern from `test_record_exercise_result_triggers_background_flush`,
   - remove sleep-based “let it settle” synchronization from auto-flush tests,
   - stop closing `svc._local` directly where the service owns that store,
   - assert completion/state through service-owned mechanisms.
7. Add regression coverage for at least these behaviors:
   - auto-flush is scheduled and can be awaited/observed without monkeypatching global task creation,
   - `close()` drains or cancels in-flight background work before SQLite teardown,
   - no follow-up SQLite work runs after service shutdown starts,
   - the previous warning reproducer no longer emits `PytestUnhandledThreadExceptionWarning`.
8. Finish with package-local validation, including full `make check` and explicit verification that the warning is gone.

## What Counts As The Correct Fix

### Required

- deterministic ownership of background tasks created by `DatabaseCacheService`
- orderly shutdown sequence: stop/finish owned tasks, then close owned SQLite resources, then clear service state
- tests that model real package lifecycle instead of manually fabricating partially closed coroutines
- regression coverage for service close + background flush lifecycle

### Forbidden

- `asyncio.sleep(...)` or longer timeouts as the stabilization strategy
- `filterwarnings`, ignoring warnings, or accepting the warning as harmless
- `xfail`, `skip`, or reducing assertions
- direct teardown shortcuts that bypass the public service lifecycle when the service owns the resource
- changes in `packages/database`

## Acceptance Criteria

- `DatabaseCacheService.close()` fully satisfies the package contract: owned background work is stopped or completed before owned local-store shutdown completes.
- `record_exercise_result()` auto-flush remains functional, but its lifecycle is observable/testable without monkeypatching global `asyncio.create_task` and without timing sleeps.
- Any stale-cache background refresh path follows the same lifecycle guarantees as background flush.
- Package-local tests and fixtures no longer bypass the public lifecycle in ways that can leave SQLite worker-thread activity racing event-loop teardown.
- `packages/database_cache -> make check` is fully green.
- Final validation shows no reproducible `PytestUnhandledThreadExceptionWarning` and no `RuntimeError: Event loop is closed` from the `aiosqlite` worker thread.
- No file outside `packages/database_cache` is modified.
- `packages/database` remains read-only and untouched.

## Validation Gates

Run these from `packages/database_cache` as part of the implementation handoff:

1. Narrow reproducer for the original warning path, promoted to hard-fail on the warning category.
2. Relevant unit/integration tests covering background flush lifecycle.
3. Full package gate:
   - `make check`
4. Explicit confirmation that the final runs produce:
   - no reproducible `PytestUnhandledThreadExceptionWarning`
   - no `RuntimeError: Event loop is closed`
   - no lint/test regressions

Recommended warning-focused validation command shape:

```bash
uv run pytest tests/unit/database_cache/test_service.py -k test_record_exercise_result_triggers_background_flush -W error::pytest.PytestUnhandledThreadExceptionWarning
```

Then finish with:

```bash
make check
```

## Risks

- The warning may be caused by multiple package-local lifecycle shortcuts, not one isolated line.
- Tightening shutdown ordering may expose hidden tests that were previously passing only because of incidental event-loop timing.
- Fixing the unit-test warning path may require parallel cleanup of integration tests that currently close service-owned resources incorrectly.

## Blockers / Escalation Conditions

Stop and escalate instead of working around the problem if any of the following becomes true:

- the remaining warning can only be fixed by changing `packages/database` or another out-of-scope package
- the documented `database_cache` lifecycle contract conflicts with the code path required for a correct fix
- the only apparent way to get green is warning suppression, sleeps, timeout inflation, xfail, or skip
- the warning root cause is proven to be external infrastructure or tooling rather than package-owned lifecycle behavior

## Done Definition

This task is done only when `packages/database_cache` keeps its green `make check`, the package-owned async lifecycle is deterministic, the specific `aiosqlite` worker-thread teardown warning is no longer reproducible, and all work stays inside `packages/database_cache` with `packages/database` left untouched.
