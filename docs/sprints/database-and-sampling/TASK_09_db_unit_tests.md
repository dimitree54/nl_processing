---
Task ID: `T9`
Title: `Unit tests for DatabaseService and ExerciseProgressStore`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T5, T6`
Parallelizable: `yes, with T10`
Owner: `Developer`
Status: `done`
---

## Goal / value

Unit tests validate DatabaseService and ExerciseProgressStore logic with a mocked backend. No real database connections — pure logic testing for deduplication, feedback generation, async translation task creation, word reconstruction, filtering, score aggregation, and error handling.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — all FRs tested at unit level
- Architecture: `nl_processing/database/docs/architecture_database.md` — Test Strategy: Unit Tests section

## Preconditions

- T5 complete (DatabaseService)
- T6 complete (ExerciseProgressStore)
- T7 complete (CachedDatabaseService — include basic cache tests)

## Non-goals

- No real database connections
- No testing of NeonBackend SQL (that's T10)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `tests/unit/database/` — create directory + test files
- `tests/unit/database/__init__.py` — create (empty)
- `tests/unit/database/conftest.py` — create (shared fixtures)
- `tests/unit/database/test_service.py` — DatabaseService unit tests
- `tests/unit/database/test_exercise_progress.py` — ExerciseProgressStore unit tests
- `tests/unit/database/test_feedback.py` — AddWordsResult generation tests (optional, can be in test_service)

**FORBIDDEN — this task must NEVER touch:**

- Any other module's code or tests
- `nl_processing/database/` source files (already complete)
- Tests for other modules

**Test scope:**

- Tests go in: `tests/unit/database/`
- Test command: `make check` (runs `uv run pytest -n auto tests/unit` which includes these)

## Touched surface (expected files / modules)

- `tests/unit/database/__init__.py` (new, empty)
- `tests/unit/database/conftest.py` (new)
- `tests/unit/database/test_service.py` (new)
- `tests/unit/database/test_exercise_progress.py` (new)

## Dependencies and sequencing notes

- Depends on T5, T6, T7 (implementation must exist to test)
- Can run in parallel with T10 (different test dirs, different concerns)

## Third-party / library research (mandatory for any external dependency)

- **Library**: pytest >=9.0.2 (already in dev dependencies)
- **Library**: pytest-asyncio >=1.3.0 (already in dev dependencies)
  - `@pytest.mark.asyncio` for async test functions
- **Library**: pytest monkeypatch (builtin fixture)
  - Used to set `DATABASE_URL` env var in unit tests

## Implementation steps (developer-facing)

1. **Create `tests/unit/database/` directory with `__init__.py` (empty).**

2. **Create `tests/unit/database/conftest.py`:**
   - Define a `MockBackend(AbstractBackend)` that implements all abstract methods with in-memory data structures (dicts/lists)
   - This is the backbone of all unit tests — allows testing service logic without a real DB
   - The mock should track calls and return predictable results
   - Define a `MockTranslator` that mimics `WordTranslator.translate()` — returns predictable translations without API calls
   - Define fixtures: `mock_backend`, `mock_translator`, `db_service` (DatabaseService with injected mock backend)
   - **Important**: To inject mock backend, tests need to patch `DatabaseService._backend` after construction (or monkeypatch the `NeonBackend` constructor). Recommend: monkeypatch `os.environ` to set `DATABASE_URL="mock://test"`, then replace `_backend` attribute post-construction.

3. **Create `tests/unit/database/test_service.py`:**
   - Test: `add_words` with new words → returns AddWordsResult with `new_words` populated
   - Test: `add_words` with existing words → returns AddWordsResult with `existing_words` populated
   - Test: `add_words` with mix of new and existing → both lists populated correctly
   - Test: `add_words` with empty list → returns empty AddWordsResult
   - Test: `add_words` creates user-word associations for all words
   - Test: `add_words` triggers async translation task for new words only
   - Test: `get_words` returns WordPair list with correct Word objects
   - Test: `get_words` excludes untranslated words (logs warning)
   - Test: `get_words` with `word_type` filter
   - Test: `get_words` with `limit`
   - Test: `get_words` with `random=True`
   - Test: constructor raises `ConfigurationError` when `DATABASE_URL` not set
   - Test: `CachedDatabaseService` caches `get_words` results
   - Test: `CachedDatabaseService` clears cache on `add_words`
   - Test: `CachedDatabaseService` does NOT cache `random=True` queries

4. **Create `tests/unit/database/test_exercise_progress.py`:**
   - Test: `increment` with delta=+1 succeeds
   - Test: `increment` with delta=-1 succeeds
   - Test: `increment` with delta=0 raises `ValueError`
   - Test: `increment` with delta=2 raises `ValueError`
   - Test: `increment` for non-existent word raises `DatabaseError`
   - Test: `get_word_pairs_with_scores` returns correct ScoredWordPair list
   - Test: missing scores default to 0
   - Test: empty `exercise_types` list → scores dict is empty
   - Test: constructor raises `ConfigurationError` when `DATABASE_URL` not set

5. **200-line limit per file**: Each test file should be under 200 lines. Architecture spec lists 4 test files — split if needed.

6. Run `make check` — all new unit tests must pass, existing 26 tests unaffected.

## Production safety constraints (mandatory)

- **Database operations**: None — all mocked.
- **Resource isolation**: N/A — no real resources.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follows existing test patterns (see `tests/unit/translate_word/conftest.py` and `test_word_translator.py` for established mocking patterns).
- **No regressions**: New tests only — existing tests unaffected.

## Error handling + correctness rules (mandatory)

- Test both happy paths and error paths (ConfigurationError, ValueError, DatabaseError).
- No `pytest.skip` — all tests must be executable.
- Use `monkeypatch.setenv("DATABASE_URL", "mock://test")` for env var setup.

## Zero legacy tolerance rule (mandatory)

- No old test files to clean up.

## Acceptance criteria (testable)

1. `tests/unit/database/` directory exists with `__init__.py`, `conftest.py`, and test files.
2. At least 15 unit tests covering DatabaseService, CachedDatabaseService, and ExerciseProgressStore.
3. All tests use mocked backend — no real database connections.
4. Tests cover: add_words deduplication, feedback generation, user-word association, async translation trigger, get_words filtering, get_words exclusion of untranslated words, cache behavior, exercise progress increment validation, score defaults.
5. Error path tests: ConfigurationError, ValueError for invalid delta, DatabaseError for missing word.
6. All test files under 200 lines.
7. `make check` passes (26 existing + new unit tests).

## Verification / quality gates

- [ ] Test directory created with conftest
- [ ] MockBackend implements all AbstractBackend methods
- [ ] 15+ unit tests pass
- [ ] No real DB connections
- [ ] All files under 200 lines
- [ ] `make check` passes

## Edge cases

- MockBackend must handle `ON CONFLICT` semantics (add_word returns None for duplicates).
- Async translation task — test that `asyncio.create_task` is called but don't await the task in unit tests (mock the translator to return immediately).
- CachedDatabaseService with `cache_max_size=0` — all calls should bypass cache.

## Notes / risks

- **Risk**: Mocking internal `_backend` attribute is fragile.
  - **Mitigation**: Accept the coupling for unit tests — it's testing internal logic. Integration tests (T10) test the real path.
