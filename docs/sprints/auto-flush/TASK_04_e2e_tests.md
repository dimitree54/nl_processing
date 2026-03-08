---
Task ID: `T4`
Title: `E2E test for auto-flush against real Neon`
Sprint: `2026-03-08_auto-flush`
Module: `database_cache`
Depends on: `T1`
Parallelizable: `yes, with T2 and T3`
Owner: `Developer`
Status: `planned`
---

## Goal / value

An E2E test verifies that after `record_exercise_result()` is called and a brief wait occurs, the score event is automatically flushed to the real Neon test database — without an explicit `flush()` call. This validates the auto-flush feature end-to-end against real infrastructure.

## Context (contract mapping)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` — FR19 (auto-flush after write), FR25 (auto-flush delivers events)
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — E2E test strategy: "record_exercise_result() auto-flushes to Neon in background"
- Module spec: `nl_processing/database_cache/docs/architecture_database_cache.md`

## Preconditions

- T1 is complete: `record_exercise_result()` calls `asyncio.create_task(self._background_flush())`
- Existing E2E test infrastructure: `tests/e2e/database_cache/conftest.py` provides `make_cache_service`, `WORDS`, `db_ready` fixture
- Doppler environment configured with test Neon credentials

## Non-goals

- Do not test flush retry/failure logic at E2E level
- Do not test cold-start or refresh behaviour (already covered by existing E2E tests)
- Do not modify production code

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/e2e/database_cache/test_full_loop.py` — add new test function

**FORBIDDEN — this task must NEVER touch:**
- Any file in `nl_processing/database_cache/`
- Any other test file or conftest
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/e2e/database_cache/`
- Test command: `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `tests/e2e/database_cache/test_full_loop.py`

## Dependencies and sequencing notes

- Depends on T1 because the test exercises the auto-flush code path added in T1
- Can run in parallel with T2 and T3 because they modify different test files

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncio` (Python stdlib)
  - **`asyncio.sleep` docs**: https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep
  - Usage: `await asyncio.sleep(0.1)` — brief wait to allow the background flush task to complete over the network
- **Neon test database**: Accessed via Doppler-managed `DATABASE_URL` environment variable. The `doppler run --` prefix in the test command injects test credentials.
- **Existing pattern**: The existing `test_full_lifecycle_init_read_write_flush` test in the same file does `record_exercise_result()` → explicit `flush()`. The new test omits the explicit `flush()` and verifies auto-flush instead.

## Implementation steps (developer-facing)

1. Open `tests/e2e/database_cache/test_full_loop.py`.

2. Add import at the top (merge with existing):
   ```python
   import asyncio
   ```

3. Add test: **`test_auto_flush_delivers_to_neon`**

   This test verifies that after `record_exercise_result()` + a brief wait, the event is flushed to Neon without an explicit `flush()` call:

   ```python
   @pytest.mark.asyncio
   @pytest.mark.usefixtures("db_ready")
   async def test_auto_flush_delivers_to_neon(tmp_path: Path) -> None:
       """record_exercise_result() auto-flushes score events to Neon without explicit flush()."""
       user_id = f"e2e_cache_{uuid4()}"
       await _seed(user_id)
       cache = make_cache_service(user_id, tmp_path)
       await cache.init()

       # Record a result — auto-flush should trigger in background
       await cache.record_exercise_result(
           source_word=Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL),
           exercise_type="flashcard",
           delta=1,
       )

       # Wait for auto-flush to complete (poll with bounded retry)
       for _ in range(50):
           status = await cache.get_status()
           if status.pending_events == 0:
               break
           await asyncio.sleep(0.1)
       else:
           pytest.fail(f"Auto-flush did not complete within 5s; pending_events={status.pending_events}")

       # Verify: refresh from Neon to confirm remote state matches
       await cache.refresh()
       scored = await cache.get_word_pairs_with_scores()
       scores_by_form = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored}
       assert scores_by_form["tafel"] == 1
       assert scores_by_form["stoel"] == 0
       assert scores_by_form["lamp"] == 0
   ```

4. Run `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v` to confirm all tests pass.

5. Run `make check` to confirm full quality gate.

## Production safety constraints (mandatory)

- **Database operations**: E2E tests use a **separate Neon test database** accessed via Doppler-managed credentials (`doppler run --`). The test database is distinct from the production database.
- **Resource isolation**: Cache files are in pytest's `tmp_path`. Neon test credentials are managed by Doppler and point to a test project/branch.
- **Migration preparation**: N/A — no schema changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Test reuses existing `_seed()`, `make_cache_service`, `WORDS` helpers and the `db_ready` fixture from conftest.
- **Correct libraries only**: `asyncio` — Python stdlib.
- **Correct file locations**: Test added to existing `test_full_loop.py` (the file that covers full lifecycle E2E tests).
- **No regressions**: Existing E2E tests remain unchanged; new test is additive.

## Error handling + correctness rules (mandatory)

- Tests do not silence errors — they assert specific outcomes.
- The polling loop uses `pytest.fail()` with a diagnostic message if the timeout is exceeded.
- No blanket try/catch in test code.

## Zero legacy tolerance rule (mandatory)

- No dead code introduced — the test directly verifies FR19 at E2E level.
- No deprecated test patterns.

## Acceptance criteria (testable)

1. `test_auto_flush_delivers_to_neon` exists and passes — verifies that `record_exercise_result()` auto-flushes to Neon without an explicit `flush()` call.
2. After auto-flush completes, `pending_events == 0`.
3. After refresh from Neon, the flushed score is visible and correct (exactly 1, not doubled).
4. All existing E2E tests in `tests/e2e/database_cache/` continue to pass.
5. `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v` is green.
6. `make check` passes.

## Verification / quality gates

- [ ] E2E test added: 1 new test in `test_full_loop.py`
- [ ] Existing E2E tests unbroken
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Test command: `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v`

## Edge cases

- **Auto-flush takes longer than expected**: The test uses a bounded polling loop (50 iterations × 0.1s = 5s max) instead of a fixed sleep. This makes it robust against variable network latency.
- **Auto-flush fails**: The test would fail at the polling loop with a clear diagnostic message. This is correct — if auto-flush cannot deliver to Neon, the test should fail.
- **Existing E2E tests call `record_exercise_result()` then explicit `flush()`**: These continue to work fine. The auto-flush runs in background and the explicit `flush()` is a no-op if auto-flush already completed (idempotent by design).

## Notes / risks

- **Risk**: E2E test is flaky due to network latency to Neon.
  - **Mitigation**: Bounded polling loop with 5s timeout. If consistently flaky, the timeout can be increased. The existing E2E tests already depend on Neon connectivity, so this test has the same reliability profile.
- **Risk**: Existing E2E tests now spawn background flush tasks that interfere.
  - **Mitigation**: The existing tests call `flush()` explicitly after `record_exercise_result()`. The auto-flush and explicit flush use the same lock — if auto-flush runs first, the explicit `flush()` is a no-op. If explicit `flush()` runs first, the auto-flush is a no-op. Both orderings are safe.
