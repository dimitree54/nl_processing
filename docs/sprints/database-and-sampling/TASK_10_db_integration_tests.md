---
Task ID: `T10`
Title: `Integration tests for database module against real Neon DB`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T8`
Parallelizable: `yes, with T9`
Owner: `Developer`
Status: `done`
---

## Goal / value

Integration tests validate NeonBackend CRUD operations, table creation/deletion, and latency benchmarks against a real Neon PostgreSQL database. These are the primary quality gate for database correctness.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — NFR10-NFR14 (testing strategy), NFR1 (200ms latency)
- Architecture: `nl_processing/database/docs/architecture_database.md` — Test Strategy: Integration Tests, Doppler Environment Strategy

## Preconditions

- T8 complete (testing utilities: reset_database, drop_all_tables, count helpers)
- T4 complete (NeonBackend implementation)
- T5 complete (DatabaseService)
- T6 complete (ExerciseProgressStore)
- Doppler `dev` environment configured with `DATABASE_URL` pointing to `nl_processing_dev` Neon database

## Non-goals

- No e2e tests with real translation (that's T11)
- No unit-level mocking
- No testing of other modules

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `tests/integration/database/` — create directory + test files
- `tests/integration/database/__init__.py` — create (empty)
- `tests/integration/database/conftest.py` — create (shared fixtures with DB setup/teardown)
- `tests/integration/database/test_neon_backend.py` — NeonBackend CRUD tests
- `tests/integration/database/test_table_creation.py` — create/drop tables tests
- `tests/integration/database/test_latency.py` — 200ms latency benchmark
- `tests/integration/database/test_exercise_scores.py` — score table CRUD + upsert

**FORBIDDEN — this task must NEVER touch:**

- Any module source code
- Tests for other modules
- Production database

**Test scope:**

- Tests go in: `tests/integration/database/`
- Test command: `doppler run -- uv run pytest -n auto tests/integration` (runs as part of `make check`)
- All tests require `DATABASE_URL` from Doppler dev environment

## Touched surface (expected files / modules)

- `tests/integration/database/__init__.py` (new, empty)
- `tests/integration/database/conftest.py` (new)
- `tests/integration/database/test_neon_backend.py` (new)
- `tests/integration/database/test_table_creation.py` (new)
- `tests/integration/database/test_latency.py` (new)
- `tests/integration/database/test_exercise_scores.py` (new)

## Dependencies and sequencing notes

- Depends on T8 (testing utilities for setup/teardown)
- T11 (e2e tests) depends on this (confirms DB operations work before full flow tests)
- T14 (sampling integration) depends on this (confirms DB fixtures work)

## Third-party / library research (mandatory for any external dependency)

- **Library**: pytest-asyncio (already installed)
  - `@pytest.mark.asyncio` for async test functions
- **Library**: asyncpg (already installed) — used implicitly via NeonBackend
- **Service**: Neon PostgreSQL (dev database via Doppler)
  - Connection via `DATABASE_URL` env var
  - `doppler run --` injects the var at test time

## Implementation steps (developer-facing)

1. **Create `tests/integration/database/` directory with `__init__.py` (empty).**

2. **Create `tests/integration/database/conftest.py`:**
   - Define an async fixture that calls `reset_database(["nl", "ru"], [("nl", "ru")])` before each test module (or test session)
   - Define a teardown that calls `drop_all_tables(["nl", "ru"], [("nl", "ru")])` after all tests
   - Use `@pytest.fixture(scope="module")` or `scope="session"` for efficiency (avoid resetting between every test — reset once, then each test operates on the shared state)
   - Provide a `database_service` fixture: `DatabaseService(user_id="test_user")` with monkeypatched env var

3. **Create `tests/integration/database/test_table_creation.py`:**
   - Test: `create_tables()` creates all expected tables (words_nl, words_ru, translations_nl_ru, user_words, user_word_exercise_scores_nl_ru)
   - Test: `create_tables()` is idempotent (call twice, no error)
   - Test: `drop_all_tables()` removes all tables
   - Test: `reset_database()` leaves clean empty tables
   - Verify table existence by querying information_schema or attempting inserts

4. **Create `tests/integration/database/test_neon_backend.py`:**
   - Test: `add_word` inserts a word and returns an id
   - Test: `add_word` for duplicate returns None
   - Test: `get_word` retrieves an inserted word
   - Test: `get_word` for non-existent word returns None
   - Test: `add_translation_link` creates a link between source and target word
   - Test: `add_user_word` creates user-word association
   - Test: `get_user_words` returns correct words for a user
   - Test: `get_user_words` with word_type filter
   - Test: `get_user_words` with limit
   - Test: `get_user_words` with random ordering

5. **Create `tests/integration/database/test_latency.py`:**
   - Test: add 50 words and measure p95 latency — assert ≤200ms per operation
   - Use `time.perf_counter()` for wall-clock timing
   - Run sequentially (not parallel) to get accurate timings
   - **Note**: If latency exceeds 200ms, the test FAILS — this is a hard requirement. Developer must report to Dima.

6. **Create `tests/integration/database/test_exercise_scores.py`:**
   - Test: `increment_user_exercise_score` creates new score row (upsert)
   - Test: `increment_user_exercise_score` updates existing score
   - Test: score starts at 0, increments to +1 with delta=+1
   - Test: score decrements with delta=-1
   - Test: `get_user_exercise_scores` returns correct scores per exercise type
   - Test: `get_user_exercise_scores` with multiple exercise types
   - Test: `get_user_exercise_scores` returns empty for no scores

7. **200-line limit per file**: Keep each test file focused. Architecture spec shows 4 integration test files — stay within 200 lines each.

8. Run `doppler run -- make check` — verify integration tests pass against real Neon dev database.

## Production safety constraints (mandatory)

- **Database operations**: All reads/writes target the dev Neon database only (`nl_processing_dev` via Doppler `dev` env).
- **Resource isolation**: `doppler run --` ensures `DATABASE_URL` points to dev database. Production database (`nl_processing_prd`) is NEVER accessible in dev environment.
- **Setup/teardown**: `reset_database()` at start, `drop_all_tables()` at end — dev database always left clean.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses testing utilities from T8 for setup/teardown.
- **No regressions**: New test files only.
- **Correct file locations**: `tests/integration/database/` per architecture.

## Error handling + correctness rules (mandatory)

- Tests verify real database behavior — no mocks.
- Failed tests mean real bugs — fix the code, not the test.

## Zero legacy tolerance rule (mandatory)

- No old test files to clean up.

## Acceptance criteria (testable)

1. `tests/integration/database/` directory exists with conftest and 4 test files.
2. All test files under 200 lines.
3. Integration tests connect to real Neon dev database via `DATABASE_URL`.
4. Table creation/deletion tests pass.
5. NeonBackend CRUD tests pass (add, get, dedup, links, user words).
6. Latency benchmark: p95 of 50 add operations ≤ 200ms.
7. Exercise score tests pass (upsert, read, multi-exercise).
8. Dev database is left clean after test run (drop_all_tables in teardown).
9. `make check` passes (26 existing + new unit + new integration tests).

## Verification / quality gates

- [ ] 4 integration test files created
- [ ] conftest has reset/teardown fixtures
- [ ] All tests pass against real Neon dev DB
- [ ] Latency benchmark passes (p95 ≤ 200ms)
- [ ] Dev database left clean
- [ ] All files under 200 lines
- [ ] `make check` passes

## Edge cases

- Cold start latency on Neon — first connection may be slow. Run a warmup query in conftest before timed tests.
- Concurrent test runners (pytest-xdist) hitting the same dev DB — use unique user_ids per test to avoid cross-contamination, or run integration tests without `-n auto` (sequentially).
- Network issues — tests will fail with `DatabaseError`. No silent fallback.

## Notes / risks

- **Risk**: pytest-xdist parallelism may cause database race conditions.
  - **Mitigation**: Integration tests can use `-n 1` (sequential) if parallelism causes issues. The Makefile uses `-n auto` — if DB tests conflict, adjust conftest to use unique table prefixes or run DB tests sequentially.
- **Risk**: Neon cold start causes latency spike on first connection.
  - **Mitigation**: Warmup connection in conftest fixture before latency tests.
