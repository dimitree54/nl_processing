---
Task ID: T10
Title: Write integration tests for `database_cache`
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T9
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Write integration tests that verify `database_cache` behavior with file-based SQLite (persistent across test restarts) and mocked remote `ExerciseProgressStore`. These tests validate: SQLite persistence and restart recovery, refresh rebuild with pending-event overlay, flush retry behavior, and exercise-type mismatch detection.

## Context (contract mapping)

- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Test Strategy > Integration Tests":
  - SQLite local persistence and restart recovery
  - refresh rebuild + pending-event overlay
  - flush retry behavior with repeated remote failures
  - changed `exercise_types` metadata triggers rebuild path
- Requirements: NFR13 ("Integration tests verify refresh/flush behavior against a local embedded database plus mocked remote interfaces")

## Preconditions

- T9 complete (unit tests pass, test patterns established in conftest)

## Non-goals

- Testing with real Neon DB (that's E2E, T11)
- Retesting pure logic already covered by unit tests

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/integration/database_cache/` — create this directory and all test files within

**FORBIDDEN — this task must NEVER touch:**
- Any module source code
- Any other test directories
- Any config files

**Test scope:**
- Tests go in: `tests/integration/database_cache/`
- Test command: `uv run pytest tests/integration/database_cache/ -x -v`
- NEVER run tests from other modules during development

## Touched surface (expected files / modules)

- `tests/integration/database_cache/__init__.py` (new, empty)
- `tests/integration/database_cache/conftest.py` (new — fixtures with file-based SQLite)
- `tests/integration/database_cache/test_persistence.py` (new)
- `tests/integration/database_cache/test_refresh_rebuild.py` (new)
- `tests/integration/database_cache/test_flush_retry.py` (new)

## Dependencies and sequencing notes

- Depends on T9 (unit tests pass, shared fixtures/patterns established)
- T11 (E2E tests) depends on this task

## Third-party / library research (mandatory for any external dependency)

- **pytest `tmp_path` fixture**: https://docs.pytest.org/en/stable/how-to/tmp_path.html — provides a temporary directory unique to each test invocation. File-based SQLite DBs are created here for persistence tests.
- **aiosqlite file-based**: `aiosqlite.connect(str(tmp_path / "test.db"))` — creates a real file. The same path can be reopened to test persistence across "restarts".

## Implementation steps (developer-facing)

1. Create `tests/integration/database_cache/` directory with `__init__.py` (empty).

2. Create `tests/integration/database_cache/conftest.py`:
   - `MockProgressStore` (reuse the same pattern from unit test conftest, or import if appropriate — but typically integration conftest is self-contained).
   - Fixture `db_path(tmp_path)` — returns a path to a SQLite file in `tmp_path`.
   - Fixture `mock_progress_store()` — returns a configurable `MockProgressStore`.

3. Create `tests/integration/database_cache/test_persistence.py`:
   - **Test: SQLite file persists across close/reopen**
     - Open a `LocalStore` with a file path, write data, close it.
     - Reopen the same file path, verify data is still there.
   - **Test: Pending events survive restart**
     - Record several exercise results, close the store.
     - Reopen, verify `get_pending_events()` returns the same events.
   - **Test: Cache metadata survives restart**
     - Write metadata (exercise_types, timestamps), close.
     - Reopen, verify metadata is intact.

4. Create `tests/integration/database_cache/test_refresh_rebuild.py`:
   - **Test: Refresh replaces snapshot atomically**
     - Load initial snapshot (5 word pairs). Refresh with a different snapshot (3 word pairs). Verify only the 3 new pairs exist.
   - **Test: Refresh preserves pending events**
     - Record local exercise results (creates pending events). Refresh. Verify pending events still exist and local scores reflect both new remote scores + pending deltas.
   - **Test: Changed exercise_types triggers rebuild**
     - Init with exercise_types=["flashcard"]. Close. Re-init with exercise_types=["flashcard", "multiple_choice"]. Verify metadata updated and refresh triggered.

5. Create `tests/integration/database_cache/test_flush_retry.py`:
   - **Test: Successful flush marks events as flushed**
     - Record events. Flush with a mock progress store that succeeds. Verify events are marked flushed.
   - **Test: Failed flush keeps events pending for retry**
     - Record events. Flush with a mock that raises on the first event. Verify first event stays pending (with `last_error` set), remaining events still processed.
   - **Test: Repeated flush of same events is idempotent**
     - Flush successfully. Flush again. Verify no duplicate calls to `apply_score_delta()`.

6. Run `uv run pytest tests/integration/database_cache/ -x -v` — all tests must pass.

7. Run `make check` — all linters + full test suite must pass.

## Production safety constraints (mandatory)

- **Database operations**: File-based SQLite in `tmp_path` only. No remote connections (progress store is mocked).
- **Resource isolation**: `tmp_path` is unique per test run — no collision with production.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow existing integration test patterns from `tests/integration/database/`.
- **Correct libraries only**: pytest, pytest-asyncio (already in dev dependencies).
- **Correct file locations**: `tests/integration/database_cache/`.
- **No regressions**: New test files.

## Error handling + correctness rules (mandatory)

- Test error scenarios explicitly (flush failure, corrupt metadata).
- Verify errors are propagated correctly (not swallowed).

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove.

## Acceptance criteria (testable)

1. Directory `tests/integration/database_cache/` exists with `__init__.py`, `conftest.py`, and at least 3 test files.
2. All integration tests pass: `uv run pytest tests/integration/database_cache/ -x -v`.
3. Tests verify: file-based SQLite persistence, restart recovery, refresh rebuild + pending overlay, flush retry, exercise-type change detection.
4. All SQLite files created in `tmp_path` (no persistent files left behind).
5. No real Neon connections.
6. Each test file is ≤ 200 lines.
7. `make check` passes.

## Verification / quality gates

- [ ] Integration tests pass: `uv run pytest tests/integration/database_cache/ -x -v`
- [ ] `make check` passes
- [ ] No new warnings introduced
- [ ] Negative-path tests exist for flush failure and exercise-type mismatch

## Edge cases

- SQLite file deleted between close and reopen — `open()` should recreate schema.
- Multiple pending events with mixed success/failure during flush.
- Refresh with zero word pairs from remote.

## Notes / risks

- **Risk**: `tmp_path` cleanup — pytest handles this automatically; no manual cleanup needed.
- **Risk**: File-based SQLite tests may be slower than in-memory — acceptable for integration level.
