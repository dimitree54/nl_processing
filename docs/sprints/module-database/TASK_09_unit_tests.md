---
Task ID: `T9`
Title: `Create unit tests with mocked backend`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T6`
Parallelizable: `yes, with T8, T10, T12`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Comprehensive unit tests exist for `DatabaseService` logic using a mocked `AbstractBackend`. Tests cover deduplication, feedback generation (AddWordsResult), user-word association, async translation triggering, get_words filtering, untranslated word exclusion, and error handling. No real database connection needed.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- all FRs validated via mocked backend
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Unit Tests" section: "Mock the abstract backend. Test DatabaseService logic."
- Test file structure: `tests/unit/database/` with `test_service.py`, `test_deduplication.py`, `test_feedback.py`

## Preconditions

- T6 completed: `DatabaseService` exists with all public methods.
- T3 completed: `AddWordsResult`, `WordPair`, exceptions exist.

## Non-goals

- Integration tests (T10) or e2e tests (T11)
- Testing `NeonBackend` directly (that's T10)
- Testing `CachedDatabaseService` (can be added to this task if T7 is done, or deferred)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/unit/database/__init__.py` -- create empty file
- `tests/unit/database/test_service.py` -- create test file
- `tests/unit/database/test_deduplication.py` -- create test file
- `tests/unit/database/test_feedback.py` -- create test file

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/` -- no module source code changes
- `tests/integration/`, `tests/e2e/` -- different test levels
- Tests of other modules
- Project-level config

**Test scope:**
- Tests go in: `tests/unit/database/`
- Test command: `uv run pytest tests/unit/database/ -x -v`
- NEVER run the full test suite or tests from other modules during development

## Touched surface (expected files / modules)

- `tests/unit/database/__init__.py` -- new empty file
- `tests/unit/database/test_service.py` -- new test file
- `tests/unit/database/test_deduplication.py` -- new test file
- `tests/unit/database/test_feedback.py` -- new test file

## Dependencies and sequencing notes

- Depends on T6 for `DatabaseService` implementation.
- T11 depends on this (e2e tests build on unit test confidence).
- Can run in parallel with T8, T10, T12.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` v9.x (already in dev dependencies)
  - `pytest.mark.asyncio` for async test functions
  - `monkeypatch` fixture for environment variable mocking
- **Library**: `pytest-asyncio` v1.x (already in dev dependencies)
  - Provides `asyncio_default_fixture_loop_scope = function` (configured in `pytest.ini`)
- **Mocking approach**: Create a concrete `MockBackend` class that extends `AbstractBackend` with in-memory dict storage. This is cleaner than `unittest.mock.AsyncMock` for testing async abstract methods.

## Implementation steps (developer-facing)

### 1. Create `tests/unit/database/__init__.py`

Empty file.

### 2. Create `tests/unit/database/test_service.py`

This is the main unit test file. It needs a `MockBackend` that implements `AbstractBackend` with in-memory storage.

```python
import asyncio

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.models import AddWordsResult, WordPair
from nl_processing.database.service import DatabaseService


class MockBackend(AbstractBackend):
    """In-memory mock backend for unit testing."""

    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}
        self.user_words: list[dict] = []
        self.links: dict[str, list[dict]] = {}
        self._next_id = 1

    async def create_tables(self, languages, pairs) -> None:
        for lang in languages:
            self.tables[f"words_{lang}"] = []
        for src, tgt in pairs:
            self.links[f"translations_{src}_{tgt}"] = []

    async def add_word(self, table, normalized_form, word_type):
        for row in self.tables.get(table, []):
            if row["normalized_form"] == normalized_form:
                return None  # Already exists
        row_id = self._next_id
        self._next_id += 1
        self.tables.setdefault(table, []).append(
            {"id": row_id, "normalized_form": normalized_form, "word_type": word_type}
        )
        return row_id

    async def get_word(self, table, normalized_form):
        for row in self.tables.get(table, []):
            if row["normalized_form"] == normalized_form:
                return dict(row)
        return None

    async def add_translation_link(self, table, source_id, target_id):
        self.links.setdefault(table, []).append(
            {"source_word_id": source_id, "target_word_id": target_id}
        )

    async def get_user_words(self, user_id, language, **filters):
        # Return user's words from the word table
        results = []
        for uw in self.user_words:
            if uw["user_id"] == user_id and uw["language"] == language:
                for row in self.tables.get(f"words_{language}", []):
                    if row["id"] == uw["word_id"]:
                        results.append(dict(row))
        return results

    async def add_user_word(self, user_id, word_id, language):
        for uw in self.user_words:
            if (uw["user_id"] == user_id and uw["word_id"] == word_id
                    and uw["language"] == language):
                return  # Already exists
        self.user_words.append(
            {"user_id": user_id, "word_id": word_id, "language": language}
        )
```

**Test cases for `test_service.py`**:

- `test_create_tables` -- verify `create_tables()` calls backend
- `test_add_words_new_words_returns_correct_feedback` -- add 3 new words, verify `AddWordsResult.new_words` has 3, `existing_words` is empty
- `test_add_words_records_user_associations` -- verify user-word links created
- `test_add_words_triggers_background_translation` -- verify `asyncio.Task` created for new words
- `test_add_words_empty_list` -- empty input returns empty result, no translation triggered
- `test_get_words_returns_word_pairs` -- after adding words + translations, verify `WordPair` list returned
- `test_get_words_excludes_untranslated` -- words without translation links are excluded
- `test_get_words_logs_warning_for_untranslated` -- verify WARNING logged

**Important**: To test `DatabaseService` with a mock backend, the developer must inject the mock. The simplest approach is:
1. Instantiate `DatabaseService` normally (with `monkeypatch.setenv("DATABASE_URL", "mock://")` and `monkeypatch.setenv("OPENAI_API_KEY", "test-key")`)
2. Replace `service._backend` with the `MockBackend` instance
3. Replace `service._translator` with a mock translator

### 3. Create `tests/unit/database/test_deduplication.py`

Test cases:
- `test_add_same_word_twice_first_new_second_existing` -- add "huis" twice, first call: new_words=["huis"], second call: existing_words=["huis"]
- `test_add_batch_with_duplicates_in_corpus` -- add ["huis", "boek"], then add ["huis", "water"]: second call has new_words=["water"], existing_words=["huis"]
- `test_deduplication_by_normalized_form` -- "huis" and "huis" are the same word (same normalized_form)

### 4. Create `tests/unit/database/test_feedback.py`

Test cases:
- `test_add_words_result_model_fields` -- verify `AddWordsResult` has `new_words` and `existing_words` fields
- `test_add_words_result_with_all_new` -- all words new: new_words has all, existing_words empty
- `test_add_words_result_with_all_existing` -- all words existing: new_words empty, existing_words has all
- `test_add_words_result_with_mixed` -- some new, some existing: correct split

### 5. Ensure each test file is under 200 lines

Split tests across files to stay within limits.

### 6. Run tests

```bash
uv run pytest tests/unit/database/ -x -v
```

### 7. Run `make check`

## Production safety constraints (mandatory)

- No production impact. Unit tests with mocked backend only.
- No database connections.

## Anti-disaster constraints (mandatory)

- `MockBackend` implements `AbstractBackend` interface correctly -- ensures tests validate the contract.
- Tests use `monkeypatch.setenv` for environment variables -- no real secrets needed.
- Tests follow existing patterns from `tests/unit/translate_word/`.

## Error handling + correctness rules (mandatory)

- Tests verify that `_translate_and_store` failures are logged (WARNING), not raised.
- Tests verify `get_words` excludes untranslated words.
- Tests verify `ConfigurationError` raised for missing `DATABASE_URL`.

## Zero legacy tolerance rule (mandatory)

- No legacy test files to update. All new test files.

## Acceptance criteria (testable)

1. `tests/unit/database/` directory exists with `__init__.py`
2. `test_service.py` contains tests for `DatabaseService` core methods
3. `test_deduplication.py` contains deduplication-specific tests
4. `test_feedback.py` contains `AddWordsResult` generation tests
5. All tests use mocked backend (no real DB connection)
6. All tests pass: `uv run pytest tests/unit/database/ -x -v`
7. All test files under 200 lines
8. `make check` passes 100% green

## Verification / quality gates

- [ ] All unit tests pass: `uv run pytest tests/unit/database/ -x -v`
- [ ] Ruff format and check pass on test files
- [ ] Pylint 200-line limit passes
- [ ] No new warnings introduced
- [ ] Negative-path tests exist (missing env var, empty input, untranslated words)
- [ ] `make check` passes 100% green

## Edge cases

- `MockBackend` must handle concurrent `add_word` calls correctly (sequential in unit tests, but async patterns should be safe).
- Empty `WordPair` list when no translations exist.
- `add_words` with words in different languages (should use the correct table based on `Word.language`).

## Notes / risks

- **Decision made autonomously**: Using a concrete `MockBackend` class instead of `unittest.mock.AsyncMock`. This provides better type safety and catches interface mismatches.
- **Risk**: If `DatabaseService` uses `NeonBackend` directly in `__init__` (not via dependency injection), the mock injection may require `monkeypatch` to replace the `_backend` attribute. This is acceptable for unit testing.
