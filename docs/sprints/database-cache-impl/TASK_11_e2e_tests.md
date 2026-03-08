---
Task ID: T11
Title: Write E2E tests for `database_cache`
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T10
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Write end-to-end tests that verify the full `database_cache` flow with a real Neon database (dev environment via Doppler) and file-based local SQLite. These tests validate: remote snapshot refresh → local cache reads → offline score write → later remote flush → verify idempotent replay.

## Context (contract mapping)

- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Test Strategy > E2E Tests":
  - remote snapshot → local cache → sampling-facing read
  - stale snapshot start does not block user read path
  - offline local score write → later remote flush
  - repeated flush of same `event_id` does not double-apply remotely
- Requirements: NFR14 ("E2E tests verify a full loop with real `database`")
- E2E test pattern: `tests/e2e/database/` — existing E2E tests with real Neon

## Preconditions

- T10 complete (unit + integration tests pass)
- Dev Neon database accessible via `doppler run --`
- Test user data can be set up and torn down (using `DatabaseService` or direct `ExerciseProgressStore`)

## Non-goals

- Testing SQLite in isolation (covered by integration tests)
- Performance benchmarking (can be a follow-up)
- Testing other modules

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/e2e/database_cache/` — create this directory and all test files within

**FORBIDDEN — this task must NEVER touch:**
- Any module source code
- Any other test directories
- Any config files

**Test scope:**
- Tests go in: `tests/e2e/database_cache/`
- Test command: `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v`
- NEVER run tests from other modules during development

## Touched surface (expected files / modules)

- `tests/e2e/database_cache/__init__.py` (new, empty)
- `tests/e2e/database_cache/conftest.py` (new — test data setup/teardown with real Neon)
- `tests/e2e/database_cache/test_full_loop.py` (new)

## Dependencies and sequencing notes

- Depends on T10 (integration tests pass)
- Last test task — no downstream dependencies
- Requires `doppler run --` to provide `DATABASE_URL` for dev environment

## Third-party / library research (mandatory for any external dependency)

- **Doppler CLI**: https://docs.doppler.com/docs/cli — `doppler run -- <command>` injects env vars from the configured environment.
- **Neon dev database**: Accessed via `DATABASE_URL` from Doppler `dev` environment. Same database used by existing `tests/e2e/database/` tests.
- **`ExerciseProgressStore`**: Used to set up test data in Neon (add words, set scores) before testing the cache.
- **`DatabaseService`**: May be needed to set up user words in Neon (the `add_words()` API creates word pairs for a user).

## Implementation steps (developer-facing)

1. Create `tests/e2e/database_cache/` directory with `__init__.py` (empty).

2. Create `tests/e2e/database_cache/conftest.py`:
   - Fixture to create a test user with words in the dev Neon database:
     - Use `DatabaseService` to add a few test words for a unique test user (e.g., `user_id="e2e_cache_test_{uuid}"`)
     - Exercise types: `["flashcard"]` (or whatever the dev DB supports)
   - Fixture for `DatabaseCacheService` with the test user, file-based SQLite in `tmp_path`, and real `ExerciseProgressStore`.
   - Teardown: clean up test data if needed (or use unique user IDs that don't collide).

3. Create `tests/e2e/database_cache/test_full_loop.py`:
   - **Test: Full lifecycle — init → refresh → read → write → flush**
     1. Create `DatabaseCacheService` with the test user.
     2. Call `await cache.init()` — should bootstrap refresh from real Neon.
     3. Verify `get_status()` shows `is_ready=True`, `has_snapshot=True`.
     4. Call `get_words()` — should return word pairs matching what was added to Neon.
     5. Call `get_word_pairs_with_scores()` — should return scored pairs with scores (default 0 for new words).
     6. Call `record_exercise_result()` — should update local score.
     7. Verify `get_word_pairs_with_scores()` reflects the updated score locally.
     8. Call `flush()` — should replay pending events to Neon.
     9. Verify `get_status()` shows `pending_events=0`.
   - **Test: Idempotent flush**
     1. Record an exercise result.
     2. Flush (succeeds).
     3. Flush again (should be a no-op — no pending events).
   - **Test: Refresh after flush restores remote state**
     1. Record a result, flush it to Neon.
     2. Refresh (re-download snapshot from Neon).
     3. Verify scores match what was flushed.

4. Run `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v` — all tests must pass.

5. Run `make check` — full pipeline must pass.

## Production safety constraints (mandatory)

- **Database operations**: Uses the **dev** Neon database (via Doppler dev environment). NEVER the production database.
- **Resource isolation**:
  - Unique test user IDs (e.g., `e2e_cache_test_{uuid}`) — no collision with real users.
  - SQLite file in `tmp_path` — no collision with production cache files.
  - `doppler run --` selects the `dev` environment which has a separate `DATABASE_URL`.
- **Migration preparation**: N/A — no schema changes to Neon. The `database` module's existing tables are used as-is.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow E2E test patterns from `tests/e2e/database/`.
- **Correct libraries only**: pytest, pytest-asyncio, Doppler CLI.
- **Correct file locations**: `tests/e2e/database_cache/`.
- **No regressions**: New test files.

## Error handling + correctness rules (mandatory)

- Verify actual data matches expectations (not just "no exception thrown").
- Test idempotent replay — flush same event twice should not double-increment.
- Clean error messages if dev database is unavailable.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove.

## Acceptance criteria (testable)

1. Directory `tests/e2e/database_cache/` exists with `__init__.py`, `conftest.py`, and at least 1 test file.
2. All E2E tests pass: `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v`.
3. Tests verify: full lifecycle (init → read → write → flush), idempotent flush, refresh-after-flush consistency.
4. Tests use the dev Neon database (never production).
5. Test user IDs are unique and don't collide with real data.
6. SQLite files in `tmp_path`.
7. Each test file is ≤ 200 lines.
8. `make check` passes.

## Verification / quality gates

- [ ] E2E tests pass: `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v`
- [ ] `make check` passes
- [ ] No new warnings introduced
- [ ] Tests use dev database only (verified by Doppler config)

## Edge cases

- Dev database has no words for the test user — refresh returns empty snapshot, reads return empty lists.
- Network timeout during `export_remote_snapshot()` — test should handle gracefully.
- Concurrent E2E test runs — unique user IDs prevent data collision.

## Notes / risks

- **Risk**: E2E tests make real API calls to Neon — slower and potentially flaky.
  - **Mitigation**: Use unique user IDs. Keep test data minimal. Accept that E2E tests are slower.
- **Risk**: Dev database may need tables created first.
  - **Mitigation**: Existing `database.testing` module has `create_tables()` or the dev DB is already set up from prior `database` module E2E tests.
- **Risk**: E2E test user needs words added via `DatabaseService.add_words()`, which requires `OPENAI_API_KEY` for translation.
  - **Mitigation**: `doppler run --` provides both `DATABASE_URL` and `OPENAI_API_KEY`. Alternatively, use `ExerciseProgressStore` directly if words already exist in dev DB, or add words with pre-translated pairs via backend SQL.
