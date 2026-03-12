---
Task ID: `T6`
Title: `E2E tests for personal vocab, progress summary, and delete`
Sprint: `2026-03-12_cache-personal-vocab`
Module: `database_cache`
Depends on: `T3, T4, T5`
Parallelizable: no
---

## Goal / value

Validate the full lifecycle of the new cache APIs (`list_personal_words()`, `get_progress_summary()`, `delete_word()`, `delete_words()`) against a real Neon database and file-based SQLite. These tests confirm that the cache correctly mirrors remote state for personal-vocabulary reads (including `added_at`), computes accurate progress summaries, and executes remote-first deletes that prune local state correctly.

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — FR-7, FR-8, FR-9, FR-10, AC-4, AC-5, AC-6
- Module spec: `docs/module-spec.md` — QA-4, QA-5, QA-6
- E2E testing strategy: Full lifecycle with real Neon + SQLite

## Preconditions

- T3 (list_personal_words) is complete
- T4 (progress_summary) is complete
- T5 (delete_apis) is complete
- E2E test infrastructure exists: `tests/e2e/database_cache/conftest.py` with `db_ready`, `make_database_service()`, `make_cache_service()`
- Real Neon test database is accessible via `DATABASE_URL` env var

## Non-goals

- Testing internal implementation details (covered by unit/integration tests)
- Testing remote-only behavior (that's the `database` package's responsibility)
- Testing SQLite persistence edge cases (covered by integration tests)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/e2e/database_cache/` — E2E tests
- `tests/e2e/database_cache/conftest.py` — E2E test fixtures (may need to update `make_cache_service()`)

**FORBIDDEN — this task must NEVER touch:**
- `src/nl_processing/database_cache/` — source code (already implemented in T1–T5)
- `src/nl_processing/core/` or any `core` package file
- `src/nl_processing/database/` or any `database` package file
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/e2e/database_cache/`
- Test command: `uv run pytest tests/e2e/database_cache/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `tests/e2e/database_cache/conftest.py` — update `make_cache_service()` if needed for delete dependency injection (may need to pass `remote_db`)
- `tests/e2e/database_cache/test_full_loop.py` — add new E2E test functions

## Dependencies and sequencing notes

- Depends on T3, T4, T5 — all new APIs must be implemented before E2E testing.
- This is the final task in the sprint.
- E2E tests require real Neon database access — they will skip if `DATABASE_URL` is not set.

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries. Uses:
- `pytest` with `@pytest.mark.asyncio` — existing test framework.
- `nl_processing.database.service.DatabaseService` — used to seed test data and verify remote state.
- `nl_processing.database_cache.service.DatabaseCacheService` — the system under test.
- `nl_processing.database.models.PersonalWord`, `ExerciseProgressSummary` — return types to validate.

## Implementation steps (developer-facing)

### Step 1: Update `conftest.py` if needed

Check if `make_cache_service()` needs to pass `remote_db` for delete tests. Since `DatabaseCacheService.init()` lazily constructs a `DatabaseService` when `remote_db` is `None`, the existing `make_cache_service()` should work without changes for E2E (it will construct a real `DatabaseService` against the test database). **Verify this.**

If the E2E `make_cache_service()` does not pass `remote_db`, the `init()` will construct one from `DATABASE_URL` — which is the correct E2E behavior.

### Step 2: Add `test_list_personal_words_returns_complete_records` E2E test

```python
@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_list_personal_words_returns_complete_records(tmp_path: Path) -> None:
    """list_personal_words() returns PersonalWord objects with added_at and scores."""
    user_id = f"e2e_cache_{uuid4()}"
    await _seed(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    personal_words = await cache.list_personal_words()

    assert len(personal_words) == len(WORDS)
    for pw in personal_words:
        assert isinstance(pw, PersonalWord)
        assert pw.added_at is not None
        assert isinstance(pw.scores, dict)
        assert "flashcard" in pw.scores
        assert pw.source_word_id > 0
        assert pw.target_word_id > 0
    source_forms = {pw.pair.source.normalized_form for pw in personal_words}
    expected_forms = {w.normalized_form for w in WORDS}
    assert source_forms == expected_forms
```

### Step 3: Add `test_progress_summary_matches_reality` E2E test

```python
@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_progress_summary_matches_reality(tmp_path: Path) -> None:
    """get_progress_summary() reports correct totals and negative counts."""
    user_id = f"e2e_cache_{uuid4()}"
    await _seed(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    # All scores start at 0
    summary = await cache.get_progress_summary()
    assert "flashcard" in summary
    assert summary["flashcard"].total_words == len(WORDS)
    assert summary["flashcard"].negative_words == 0

    # Record -1 for one word
    await cache.record_exercise_result(
        source_word=WORDS[0], exercise_type="flashcard", delta=-1
    )
    summary_after = await cache.get_progress_summary()
    assert summary_after["flashcard"].negative_words == 1
    assert summary_after["flashcard"].total_words == len(WORDS)
```

### Step 4: Add `test_delete_word_e2e` E2E test

```python
@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_delete_word_removes_from_cache_and_remote(tmp_path: Path) -> None:
    """delete_word() removes the word from remote and local cache."""
    user_id = f"e2e_cache_{uuid4()}"
    await _seed(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    personal_words = await cache.list_personal_words()
    target_word = personal_words[0]
    target_id = target_word.source_word_id

    await cache.delete_word(target_id)

    # Verify locally: word is gone
    remaining = await cache.list_personal_words()
    assert len(remaining) == len(WORDS) - 1
    remaining_ids = {pw.source_word_id for pw in remaining}
    assert target_id not in remaining_ids

    # Verify progress summary updated
    summary = await cache.get_progress_summary()
    assert summary["flashcard"].total_words == len(WORDS) - 1

    # Verify after refresh: word doesn't reappear (deleted remotely)
    await cache.refresh()
    after_refresh = await cache.list_personal_words()
    assert len(after_refresh) == len(WORDS) - 1
```

### Step 5: Add `test_delete_word_with_pending_events` E2E test

```python
@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_delete_word_clears_pending_events(tmp_path: Path) -> None:
    """delete_word() also removes pending score events for the word (BR-6)."""
    user_id = f"e2e_cache_{uuid4()}"
    await _seed(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    personal_words = await cache.list_personal_words()
    target_word = personal_words[0]

    # Record a score (creates pending event)
    await cache.record_exercise_result(
        source_word=target_word.pair.source, exercise_type="flashcard", delta=1
    )

    # Delete the word
    await cache.delete_word(target_word.source_word_id)

    # Verify pending events are cleaned up
    status = await cache.get_status()
    # Pending count should be 0 (the only pending event was for the deleted word)
    assert status.pending_events == 0
```

### Step 6: Add necessary imports to test file

Add imports for `PersonalWord` from `database.models` and update the conftest import list.

### Step 7: Run E2E tests and verify

1. `uv run pytest tests/e2e/database_cache/ -x -v`
2. Verify all tests pass against real Neon.
3. Check for jscpd duplicate patterns with existing test code.

## Production safety constraints (mandatory)

- **Database operations**: E2E tests use the **testing Neon database** (via `DATABASE_URL` env var in the test environment). The `db_ready` fixture acquires an advisory lock, resets the database before the test, and drops/recreates tables after.
- **SQLite operations**: File-based SQLite in `tmp_path` — cleaned up by pytest.
- **Production isolation**: The production bot runs from a different directory with its own `DATABASE_URL`. Test fixtures explicitly reset and isolate data.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses existing `db_ready`, `make_database_service()`, `make_cache_service()`, `_seed()`, `wait_for_translations()` from E2E conftest.
- **No fixture duplication**: Uses the same conftest helpers as existing E2E tests. New tests follow the same patterns.
- **No regressions**: Existing E2E tests must continue to pass.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: Test assertions use explicit checks, not blanket `assert result` patterns.
- **No mock fallbacks**: E2E tests use real services — no mocking.
- Tests must clean up after themselves via the `db_ready` fixture.

## Zero legacy tolerance rule (mandatory)

After implementing this task:

- E2E coverage exists for all new public APIs (FR-7, FR-8, FR-9).
- The QA matrix items QA-4, QA-5, QA-6 have E2E verification.
- No dead or commented-out test code.

## Acceptance criteria (testable)

1. E2E test verifies `list_personal_words()` returns `PersonalWord` objects with `added_at`, scores, and stable IDs from real Neon.
2. E2E test verifies `get_progress_summary()` reports correct `total_words` and `negative_words` after score changes.
3. E2E test verifies `delete_word()` removes the word from both remote and local cache.
4. E2E test verifies deleted word does not reappear after `refresh()`.
5. E2E test verifies pending score events are removed on delete (BR-6).
6. All existing E2E tests continue to pass.
7. All E2E tests pass: `uv run pytest tests/e2e/database_cache/ -x -v`.

## Verification / quality gates

- [ ] E2E tests pass: `uv run pytest tests/e2e/database_cache/ -x -v`
- [ ] Existing E2E tests still pass
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] No jscpd duplicate patterns with existing test code
- [ ] Test file stays under 200 lines (current `test_full_loop.py` is 130 lines + ~80 new lines = ~210 — may need to split into `test_personal_vocab_e2e.py`)

## Edge cases

- Translation latency: `wait_for_translations()` polls with timeout. If translations take too long, the test fails with a clear timeout message.
- Advisory lock contention: If another test process holds the lock, `pg_advisory_lock` blocks until released. Tests should not be run in parallel against the same Neon database.
- Empty vocabulary after deleting all words: `list_personal_words()` returns `[]`, `get_progress_summary()` returns zero summaries.

## Notes / risks

- **Risk**: E2E tests are slow due to real Neon + translation waits.
  - **Mitigation**: Use the existing `wait_for_translations()` pattern with a 15s timeout. E2E tests are expected to be slower.
- **Risk**: `test_full_loop.py` may exceed 200 lines after adding new tests.
  - **Mitigation**: Split into `test_full_loop.py` (existing tests) and `test_personal_vocab_e2e.py` (new tests for FR-7/8/9). This also helps with jscpd — the new file has its own focused structure.
- **Risk**: `make_cache_service()` may need `remote_db` parameter for delete tests.
  - **Mitigation**: If `remote_db` is `None`, `init()` constructs a `DatabaseService` from `DATABASE_URL`. For E2E, this is the correct behavior — no conftest change needed unless the constructor API requires an explicit parameter.
