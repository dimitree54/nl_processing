---
Task ID: `T3`
Title: `Integration test for auto-flush event delivery`
Sprint: `2026-03-08_auto-flush`
Module: `database_cache`
Depends on: `T1`
Parallelizable: `yes, with T2 and T4`
Owner: `Developer`
Status: `planned`
---

## Goal / value

An integration test verifies that after `record_exercise_result()` completes and the event loop runs, pending events are automatically flushed to the (mock) remote database. This tests the full flow: local write → background task creation → `CacheSyncer.flush()` → `MockProgressStore.apply_score_delta()` — using file-backed SQLite, not in-memory.

## Context (contract mapping)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` — FR19 (auto-flush after write), FR25 (auto-flush delivers events)
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — integration test strategy: "auto-flush delivers events to remote after record_exercise_result()"
- Module spec: `nl_processing/database_cache/docs/architecture_database_cache.md`

## Preconditions

- T1 is complete: `record_exercise_result()` calls `asyncio.create_task(self._background_flush())`
- Existing integration test infrastructure in `tests/integration/database_cache/conftest.py` provides `MockProgressStore`, `make_scored_pair`, and `db_path` fixture

## Non-goals

- Do not test flush retry/failure logic (already covered by existing `test_flush_retry.py`)
- Do not test remote connectivity (that's E2E)
- Do not modify production code

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/integration/database_cache/test_flush_retry.py` — add new test function(s)

**FORBIDDEN — this task must NEVER touch:**
- Any file in `nl_processing/database_cache/`
- Any other test file or conftest
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/integration/database_cache/`
- Test command: `doppler run -- uv run pytest tests/integration/database_cache/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `tests/integration/database_cache/test_flush_retry.py`

## Dependencies and sequencing notes

- Depends on T1 because the test exercises the `asyncio.create_task` call added in T1
- Can run in parallel with T2 and T4 because they modify different test files

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncio` (Python stdlib)
  - **`asyncio.sleep` docs**: https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep
  - Usage: `await asyncio.sleep(0)` to yield to the event loop and let background tasks run
- **Library**: `nl_processing.database_cache.service.DatabaseCacheService`
  - Uses the full service rather than calling `CacheSyncer` directly — this tests the auto-flush path end-to-end at integration level
- Existing test patterns from `test_flush_retry.py`: uses `_setup_store_with_snapshot()` helper for file-backed SQLite setup

## Implementation steps (developer-facing)

1. Open `tests/integration/database_cache/test_flush_retry.py`.

2. Add import at the top (merge with existing):
   ```python
   import asyncio
   from datetime import timedelta
   from nl_processing.database_cache.service import DatabaseCacheService
   from nl_processing.core.models import Language, PartOfSpeech, Word
   ```

3. Add test: **`test_auto_flush_delivers_events_after_record`**

   This test sets up a `DatabaseCacheService` with a file-backed SQLite store and mock remote, calls `record_exercise_result()`, yields to the event loop, then verifies events reached the mock remote:

   ```python
   @pytest.mark.asyncio
   async def test_auto_flush_delivers_events_after_record(db_path: Path) -> None:
       """record_exercise_result() auto-flush pushes events to the mock remote."""
       remote = MockProgressStore(
           snapshot=[
               make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
           ]
       )
       svc = DatabaseCacheService(
           user_id="integration_auto_flush",
           source_language=Language.NL,
           target_language=Language.RU,
           exercise_types=["flashcard"],
           cache_ttl=timedelta(minutes=30),
           cache_dir=str(db_path.parent),
       )
       svc._local = LocalStore(str(db_path))
       await svc._local.open()
       svc._syncer = CacheSyncer(svc._local, remote)
       await svc._local.ensure_metadata(["flashcard"])
       await svc._syncer.refresh()
       svc._initialized = True

       word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
       await svc.record_exercise_result(source_word=word, exercise_type="flashcard", delta=1)

       # Yield to event loop so the background flush task runs
       await asyncio.sleep(0)

       assert len(remote.applied_deltas) == 1
       assert remote.applied_deltas[0]["exercise_type"] == "flashcard"
       assert remote.applied_deltas[0]["delta"] == 1

       status = await svc.get_status()
       assert status.pending_events == 0
       await svc._local.close()
   ```

4. Run `doppler run -- uv run pytest tests/integration/database_cache/ -x -v` to confirm all tests pass.

5. Run `make check` to confirm full quality gate.

## Production safety constraints (mandatory)

- **Database operations**: Integration tests use file-backed SQLite in `tmp_path` + `MockProgressStore`. No remote Neon access.
- **Resource isolation**: All cache files are in pytest's `tmp_path`. No collision with production.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Test reuses existing `MockProgressStore`, `make_scored_pair`, and `db_path` fixture from `conftest.py`. Setup pattern mirrors the existing `cache_service` fixture from the unit test conftest.
- **Correct libraries only**: `asyncio`, `datetime` — Python stdlib.
- **Correct file locations**: Test added to existing `test_flush_retry.py` (the file that covers flush behaviour).
- **No regressions**: Existing tests remain unchanged; new test is additive.

## Error handling + correctness rules (mandatory)

- Tests do not silence errors — they assert specific outcomes.
- No blanket try/catch in test code.

## Zero legacy tolerance rule (mandatory)

- No dead code introduced — the test directly verifies FR19.
- No deprecated test patterns.

## Acceptance criteria (testable)

1. `test_auto_flush_delivers_events_after_record` exists and passes — verifies that `record_exercise_result()` auto-flushes events to the mock remote.
2. The test uses file-backed SQLite (not in-memory) for integration-level validation.
3. All existing integration tests in `tests/integration/database_cache/` continue to pass.
4. `doppler run -- uv run pytest tests/integration/database_cache/ -x -v` is green.
5. `make check` passes.

## Verification / quality gates

- [ ] Integration test added: 1 new test in `test_flush_retry.py`
- [ ] Existing integration tests unbroken
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Test command: `doppler run -- uv run pytest tests/integration/database_cache/ -x -v`

## Edge cases

- **Background flush fails**: Not tested here — existing `test_failed_flush_keeps_events_pending` already covers flush failure. The auto-flush path just calls the same `flush()` method.
- **Multiple rapid writes**: Not tested at integration level (would require more complex async orchestration). The flush lock in `CacheSyncer` handles this safely.

## Notes / risks

- **Risk**: `await asyncio.sleep(0)` is insufficient for the background task to complete.
  - **Mitigation**: The mock remote's `apply_score_delta` is a single synchronous `await`. One event-loop yield is sufficient. If flaky, increase to `await asyncio.sleep(0.01)`.
