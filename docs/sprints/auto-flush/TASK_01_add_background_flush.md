---
Task ID: `T1`
Title: `Add _background_flush() and auto-flush trigger to record_exercise_result()`
Sprint: `2026-03-08_auto-flush`
Module: `database_cache`
Depends on: `—`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

After this task, every call to `record_exercise_result()` automatically starts a fire-and-forget background flush via `asyncio.create_task`. This closes the gap between the documented architecture (which specifies auto-flush) and the current implementation (which requires manual `flush()` calls).

## Context (contract mapping)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` — FR19, FR20, FR25
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Record Exercise Result" lifecycle step 5, "Local Writes Use Transactional Outbox + Auto-Flush" decision
- Module spec: `nl_processing/database_cache/docs/architecture_database_cache.md`

## Preconditions

- `service.py` exists at 177 lines with `_background_refresh()` already implemented as the pattern to follow
- `CacheSyncer.flush()` in `sync.py` already uses a lock guard (`if self._flush_lock.locked(): return`) that makes concurrent auto-flushes safe — no changes needed in `sync.py`

## Non-goals

- Do not change `CacheSyncer.flush()` or any other method in `sync.py`
- Do not change `LocalStore` or any SQLite queries
- Do not change the public interface of `DatabaseCacheService`
- Do not add or change any tests (tests are covered in T2–T4)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database_cache/service.py` — add `_background_flush()` method and `asyncio.create_task` call

**FORBIDDEN — this task must NEVER touch:**
- Any other file in `nl_processing/database_cache/`
- Any test file
- Any other module's code

**Test scope:**
- Tests go in: `tests/unit/database_cache/` (handled by T2)
- Test command: `uv run pytest tests/unit/database_cache/ -x -v`
- After this task: run `uv run pytest tests/unit/database_cache/ -x -v` to confirm existing tests still pass

## Touched surface (expected files / modules)

- `nl_processing/database_cache/service.py`

## Dependencies and sequencing notes

- No dependencies — this is the first task
- T2, T3, T4 all depend on this task completing first

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncio` (Python stdlib, no version constraint)
- **`asyncio.create_task` docs**: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
- **Usage**: `asyncio.create_task(coroutine)` — schedules the coroutine to run in the background; the calling coroutine continues immediately
- **Known gotchas**: The returned `Task` must be referenced to prevent garbage collection from cancelling it. However, the existing `_background_refresh()` usage in `init()` (line 67) already uses the same fire-and-forget pattern (`asyncio.create_task(self._background_refresh())`) without storing the reference, establishing this as the project's accepted pattern. Follow the same convention.

## Implementation steps (developer-facing)

1. Open `nl_processing/database_cache/service.py`.

2. Add a `_background_flush()` method immediately after `_background_refresh()` (after line 170). Model it exactly on `_background_refresh()`:

   ```python
   async def _background_flush(self) -> None:
       try:
           assert self._syncer is not None
           await self._syncer.flush()
       except Exception:
           _log.exception("background flush failed")
   ```

3. At the end of `record_exercise_result()`, after the `await self._local.record_score_and_event(...)` call (after line 110), add:

   ```python
   asyncio.create_task(self._background_flush())
   ```

4. Verify `service.py` is now ~184 lines (well under the 200-line pylint limit).

5. Run `uv run pytest tests/unit/database_cache/ -x -v` to confirm existing tests still pass. Note: existing tests that call `record_exercise_result()` will now spawn background tasks. These should complete quickly since the mock remote is synchronous and instant. If any test complains about unawaited tasks, that will be addressed in T2.

6. Run `make check` to verify linters, vulture, and jscpd are green.

## Production safety constraints (mandatory)

- **Database operations**: This change only affects in-process async task creation. No database connections are added or changed.
- **Resource isolation**: No new files, ports, or sockets. The background flush uses the existing `CacheSyncer` instance which is already configured.
- **Migration preparation**: N/A — no data model changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: `_background_flush()` mirrors the existing `_background_refresh()` pattern exactly — same structure, same exception handling.
- **Correct libraries only**: `asyncio` is Python stdlib; `asyncio.create_task` is already used in this file (line 67).
- **Correct file locations**: Change is in the existing `service.py`, exactly where the architecture places it.
- **No regressions**: Existing tests must pass unchanged. The `CacheSyncer.flush()` lock guard prevents any concurrency issues.

## Error handling + correctness rules (mandatory)

- `_background_flush()` catches all exceptions and logs them via `_log.exception()` — same pattern as `_background_refresh()`.
- The exception is logged, not silenced — the full traceback appears in logs.
- The method does not re-raise because it runs as a fire-and-forget background task; there is no caller to propagate to.

## Zero legacy tolerance rule (mandatory)

- No dead code introduced — `_background_flush()` is immediately used by `record_exercise_result()`.
- No code removed — `flush()` public method remains for explicit use (architecture specifies both auto and explicit flush).
- No deprecated paths — the manual `flush()` path is not deprecated, just no longer *required* for normal operation.

## Acceptance criteria (testable)

1. `record_exercise_result()` in `service.py` contains a call to `asyncio.create_task(self._background_flush())` after the local write.
2. `_background_flush()` method exists, wraps `self._syncer.flush()`, and logs exceptions without re-raising.
3. `service.py` is at or below 200 lines.
4. `uv run pytest tests/unit/database_cache/ -x -v` passes (existing tests green).
5. `make check` passes.

## Verification / quality gates

- [ ] `_background_flush()` follows the exact same pattern as `_background_refresh()`
- [ ] `asyncio.create_task` call is placed after `record_score_and_event` completes
- [ ] `service.py` line count verified ≤ 200
- [ ] Existing unit tests pass: `uv run pytest tests/unit/database_cache/ -x -v`
- [ ] Linters/formatters pass: `uv run ruff format && uv run ruff check --fix`
- [ ] Pylint line limit: `uvx pylint nl_processing/database_cache/service.py --disable=all --enable=C0302 --max-module-lines=200`
- [ ] Vulture: `uv run vulture nl_processing tests vulture_whitelist.py`
- [ ] No new warnings introduced

## Edge cases

- **Concurrent `record_exercise_result()` calls**: Each spawns its own `_background_flush()` task. The flush lock in `CacheSyncer.flush()` ensures only one flush runs at a time; additional attempts return immediately. This is safe and intentional.
- **`record_exercise_result()` called when remote is down**: The background flush fails silently (logged). Events remain pending in the local outbox and will be retried on the next `record_exercise_result()` call's auto-flush.

## Rollout / rollback (if relevant)

- Rollout: Deploy the updated `service.py`. No configuration changes needed.
- Rollback: Remove the `asyncio.create_task` line and `_background_flush()` method to restore manual-only flush.

## Notes / risks

- **Risk**: Existing unit tests spawn unwanted background tasks after this change.
  - **Mitigation**: Mock remote completes instantly, so tasks resolve quickly. If pytest warns about pending tasks, T2 will address this by either patching `create_task` or yielding to the event loop.
