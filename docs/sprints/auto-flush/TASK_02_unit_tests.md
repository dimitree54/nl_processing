---
Task ID: `T2`
Title: `Unit tests for auto-flush behaviour`
Sprint: `2026-03-08_auto-flush`
Module: `database_cache`
Depends on: `T1`
Parallelizable: `yes, with T3 and T4`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Unit tests verify that `record_exercise_result()` creates a background flush task after the local write, and that the auto-flush does not block the method's return. These tests also ensure that existing tests remain green after the T1 code change.

## Context (contract mapping)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` — FR19 (auto-flush after write), FR20 (non-blocking)
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — test strategy: "record_exercise_result() triggers background flush automatically", "auto-flush does not block record_exercise_result() return"
- Module spec: `nl_processing/database_cache/docs/architecture_database_cache.md`

## Preconditions

- T1 is complete: `_background_flush()` exists and `record_exercise_result()` calls `asyncio.create_task(self._background_flush())`
- Existing unit test fixtures in `tests/unit/database_cache/conftest.py` provide a fully-initialized `cache_service` with a `MockProgressStore`

## Non-goals

- Do not test flush retry logic (covered by existing integration tests)
- Do not test remote connectivity (that's E2E)
- Do not modify `service.py` or any production code

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/unit/database_cache/test_service.py` — add new test functions

**FORBIDDEN — this task must NEVER touch:**
- Any file in `nl_processing/database_cache/`
- Any other test file or conftest
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/unit/database_cache/`
- Test command: `uv run pytest tests/unit/database_cache/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `tests/unit/database_cache/test_service.py`

## Dependencies and sequencing notes

- Depends on T1 because the tests exercise the `asyncio.create_task` call added in T1
- Can run in parallel with T3 and T4 because they modify different test files

## Third-party / library research (mandatory for any external dependency)

- **Library**: `unittest.mock` (Python stdlib)
  - **`AsyncMock` docs**: https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock
  - **`patch` docs**: https://docs.python.org/3/library/unittest.mock.html#unittest.mock.patch
  - Usage: `unittest.mock.patch("nl_processing.database_cache.service.asyncio.create_task")` to intercept the fire-and-forget call and verify it was invoked with the correct coroutine
- **Library**: `asyncio` (Python stdlib)
  - **`asyncio.sleep(0)` docs**: https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep
  - Usage: `await asyncio.sleep(0)` yields control to the event loop, allowing any pending background tasks to execute. Used as an alternative to mocking when we want the background task to actually run.

## Implementation steps (developer-facing)

1. Open `tests/unit/database_cache/test_service.py`.

2. Add the following imports at the top (merge with existing imports):
   ```python
   import asyncio
   from unittest.mock import patch
   ```

3. Add test: **`test_record_exercise_result_triggers_background_flush`**

   This test verifies that `record_exercise_result()` calls `asyncio.create_task` after the local write:

   ```python
   @pytest.mark.asyncio
   async def test_record_exercise_result_triggers_background_flush(cache_service: DatabaseCacheService) -> None:
       """record_exercise_result() spawns a background flush task."""
       word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
       with patch("nl_processing.database_cache.service.asyncio.create_task") as mock_create_task:
           await cache_service.record_exercise_result(source_word=word, exercise_type="flashcard", delta=1)
           mock_create_task.assert_called_once()
   ```

4. Add test: **`test_auto_flush_delivers_events_to_remote`**

   This test verifies that the background flush actually delivers pending events to the mock remote:

   ```python
   @pytest.mark.asyncio
   async def test_auto_flush_delivers_events_to_remote(cache_service: DatabaseCacheService) -> None:
       """Auto-flush after record_exercise_result() pushes events to remote."""
       word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
       await cache_service.record_exercise_result(source_word=word, exercise_type="flashcard", delta=1)
       await asyncio.sleep(0)  # yield to event loop so background task runs
       status = await cache_service.get_status()
       assert status.pending_events == 0
   ```

5. Run `uv run pytest tests/unit/database_cache/ -x -v` to confirm all tests pass (both new and existing).

6. Run `make check` to confirm full quality gate.

## Production safety constraints (mandatory)

- **Database operations**: Unit tests use in-memory SQLite via `tmp_path` fixture. No remote database access.
- **Resource isolation**: Tests use pytest's `tmp_path` for cache files. No shared resources.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Tests reuse the existing `cache_service` fixture and `MockProgressStore` from `conftest.py`.
- **Correct libraries only**: `unittest.mock` and `asyncio` are Python stdlib.
- **Correct file locations**: Tests added to the existing `test_service.py` file.
- **No regressions**: Existing tests remain unchanged; new tests are additive.

## Error handling + correctness rules (mandatory)

- Tests do not silence errors — they assert specific outcomes.
- No blanket try/catch in test code.

## Zero legacy tolerance rule (mandatory)

- No dead code — all new tests verify documented requirements (FR19, FR20).
- No deprecated test patterns introduced.

## Acceptance criteria (testable)

1. `test_record_exercise_result_triggers_background_flush` exists and passes — verifies `asyncio.create_task` is called exactly once after `record_exercise_result()`.
2. `test_auto_flush_delivers_events_to_remote` exists and passes — verifies pending events reach 0 after a brief event-loop yield.
3. All existing unit tests in `tests/unit/database_cache/` continue to pass.
4. `uv run pytest tests/unit/database_cache/ -x -v` is green.
5. `make check` passes.

## Verification / quality gates

- [ ] Unit tests added: 2 new tests in `test_service.py`
- [ ] Existing unit tests unbroken
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Test command: `uv run pytest tests/unit/database_cache/ -x -v`

## Edge cases

- **Mock remote that raises**: The existing `test_record_exercise_result_updates_locally` test calls `record_exercise_result()`. After T1, this spawns a background flush. Since `MockProgressStore.apply_error` is `None` by default, the flush succeeds silently. If the mock raised, `_background_flush()` would log and swallow — no test interference.
- **Multiple rapid calls**: Not tested at unit level (integration concern). Each call spawns its own task; the flush lock handles concurrency.

## Notes / risks

- **Risk**: `await asyncio.sleep(0)` is insufficient if the background task involves multiple async steps.
  - **Mitigation**: The mock remote's `apply_score_delta` is a single `await` that completes synchronously. One event-loop yield is sufficient.
