---
Task ID: T9
Title: Write unit tests for `database_cache`
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T8
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Write comprehensive unit tests for the `database_cache` module using in-memory SQLite (`:memory:`) and mocked remote `ExerciseProgressStore`. These tests validate all local logic: staleness checks, exercise-type validation, local transaction correctness, CacheNotReadyError behavior, and status reporting.

## Context (contract mapping)

- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Test Strategy > Unit Tests":
  - stale/fresh TTL decisions
  - exercise-type validation
  - local transaction writes both score and outbox
  - `CacheNotReadyError` on true cold start
- Requirements: NFR12 ("Unit tests verify staleness checks, exercise-set validation, local score overlay, and not-ready behavior")
- Test pattern reference: `tests/unit/database/conftest.py` (MockBackend pattern), `tests/unit/sampling/conftest.py` (MockProgressStore pattern)

## Preconditions

- T8 complete (all module source files exist and the package is importable)

## Non-goals

- Testing with file-based SQLite (that's integration tests, T10)
- Testing with real Neon DB (that's E2E tests, T11)
- Testing the `database` module itself

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/unit/database_cache/` — create this directory and all test files within

**FORBIDDEN — this task must NEVER touch:**
- Any module source code
- Any other test directories
- Any config files

**Test scope:**
- Tests go in: `tests/unit/database_cache/`
- Test command: `uv run pytest tests/unit/database_cache/ -x -v`
- NEVER run the full test suite or tests from other modules during development

## Touched surface (expected files / modules)

- `tests/unit/database_cache/__init__.py` (new, empty)
- `tests/unit/database_cache/conftest.py` (new — shared fixtures)
- `tests/unit/database_cache/test_local_store.py` (new)
- `tests/unit/database_cache/test_service.py` (new)
- `tests/unit/database_cache/test_sync.py` (new)
- `tests/unit/database_cache/test_models.py` (new)

## Dependencies and sequencing notes

- Depends on T8 (module fully implemented and importable)
- T10 (integration tests) depends on this task
- Should be done before T12 (vulture) so that test symbols are visible to vulture

## Third-party / library research (mandatory for any external dependency)

- **pytest-asyncio**: Already in `pyproject.toml` (`>=1.3.0,<2`). Used for `async def test_*` functions.
  - Docs: https://pytest-asyncio.readthedocs.io/en/latest/
  - Usage: decorate async tests with `@pytest.mark.asyncio` or configure `asyncio_mode = "auto"` in `pytest.ini`.
  - Current project uses `@pytest.mark.asyncio` explicitly (see existing tests).
- **aiosqlite in-memory**: `aiosqlite.connect(":memory:")` opens an in-memory database. No file created.
  - Docs: https://aiosqlite.omnilib.dev/en/stable/

## Implementation steps (developer-facing)

1. Create `tests/unit/database_cache/` directory with `__init__.py` (empty).

2. Create `tests/unit/database_cache/conftest.py` with shared fixtures:
   - **`MockProgressStore`**: A fake that implements the two methods `database_cache` consumes:
     - `export_remote_snapshot() -> list[ScoredWordPair]` — returns configurable data
     - `apply_score_delta(event_id, source_word_id, exercise_type, delta) -> None` — tracks calls, optionally raises
   - **Helper functions**: `make_scored_pair(...)` and `make_word(...)` (follow pattern from `tests/unit/sampling/conftest.py`)
   - **`cache_service` fixture**: Creates a `DatabaseCacheService` with mocked progress store and in-memory SQLite (or tmp_path for the SQLite file), monkeypatches `DATABASE_URL` env var.

3. Create `tests/unit/database_cache/test_models.py`:
   - Test `CacheStatus` construction with all fields
   - Test `CacheStatus` serialization (Pydantic model_dump)
   - Test `CacheStatus` with None timestamps

4. Create `tests/unit/database_cache/test_local_store.py`:
   - Test schema creation (open an in-memory DB, verify tables exist)
   - Test `record_score_and_event()` writes both score and outbox in one transaction
   - Test `get_cached_word_pairs()` with filters (word_type, limit, random)
   - Test `get_cached_word_pairs_with_scores()` — missing scores default to 0
   - Test `rebuild_snapshot()` replaces data atomically
   - Test `rebuild_snapshot()` reapplies pending events after replacing scores
   - Test `get_pending_events()` returns only unflushed events
   - Test `mark_event_flushed()` updates the flushed_at timestamp
   - Test `has_snapshot()` returns False on empty DB, True after data loaded
   - Test metadata read/write

5. Create `tests/unit/database_cache/test_sync.py`:
   - Test `refresh()` calls `export_remote_snapshot()` and `rebuild_snapshot()`
   - Test `refresh()` updates metadata timestamps
   - Test `refresh()` error handling — wraps errors in `CacheSyncError`
   - Test `flush()` replays pending events via `apply_score_delta()`
   - Test `flush()` marks successful events as flushed
   - Test `flush()` keeps failed events pending (per-event error handling)
   - Test concurrent refresh skip (lock contention)
   - Test concurrent flush skip (lock contention)

6. Create `tests/unit/database_cache/test_service.py`:
   - Test constructor validates `exercise_types` non-empty
   - Test `init()` with fresh cache (bootstrap refresh)
   - Test `init()` with existing stale snapshot (background refresh triggered)
   - Test `init()` with fresh snapshot (no refresh)
   - Test `get_words()` raises `CacheNotReadyError` before init
   - Test `get_word_pairs_with_scores()` raises `CacheNotReadyError` before init
   - Test `record_exercise_result()` validates exercise_type
   - Test `record_exercise_result()` validates delta (+1 or -1 only)
   - Test `record_exercise_result()` updates local score immediately (read-after-write)
   - Test `get_status()` returns correct `CacheStatus`

7. Run `uv run pytest tests/unit/database_cache/ -x -v` — all tests must pass.

8. Run `make check` — all linters + full test suite must pass.

## Production safety constraints (mandatory)

- **Database operations**: In-memory SQLite only. No remote connections.
- **Resource isolation**: Tests use `:memory:` or `tmp_path` — no persistent files.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow test patterns from `tests/unit/database/conftest.py` and `tests/unit/sampling/conftest.py`.
- **Correct libraries only**: pytest, pytest-asyncio (already in dev dependencies).
- **Correct file locations**: `tests/unit/database_cache/`.
- **No regressions**: New test files, no existing code affected.

## Error handling + correctness rules (mandatory)

- Test both success and error paths.
- Test `CacheNotReadyError` is raised correctly (not a fallback).
- Test `ValueError` for invalid inputs.
- Test `CacheSyncError` wrapping.
- No `pytest.skip` or `pytest.mark.skip` (banned by ruff).

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove.

## Acceptance criteria (testable)

1. Directory `tests/unit/database_cache/` exists with `__init__.py`, `conftest.py`, and at least 4 test files.
2. All unit tests pass: `uv run pytest tests/unit/database_cache/ -x -v`.
3. Tests cover: staleness TTL checks, exercise-type validation, local transactional writes, `CacheNotReadyError`, score overlay after refresh, status reporting.
4. No real SQLite files created (all in-memory or `tmp_path`).
5. No real Neon connections (progress store is mocked).
6. Each test file is ≤ 200 lines.
7. `make check` passes.

## Verification / quality gates

- [ ] Unit tests pass: `uv run pytest tests/unit/database_cache/ -x -v`
- [ ] `make check` passes
- [ ] No new warnings introduced
- [ ] Negative-path tests exist for CacheNotReadyError, ValueError, CacheSyncError

## Edge cases

- Empty database (no snapshot) — reads raise `CacheNotReadyError`
- `record_exercise_result()` for word not in cache — should raise
- `refresh()` with empty remote snapshot — clears local data
- `flush()` with no pending events — no-op

## Notes / risks

- **Risk**: Test file count — architecture lists ≤10 test files per directory. With 4 test files + conftest + `__init__.py` = 6 files, well within limit.
- **Risk**: Mocking pattern for `ExerciseProgressStore` — the project injects mock backends rather than mocking the entire class. For `database_cache`, mock the `ExerciseProgressStore` at the instance level (replace `_progress_store` attribute on the syncer or service), consistent with the `MockProgressStore` pattern in `tests/unit/sampling/conftest.py`.
