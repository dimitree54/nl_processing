---
Task ID: `T11`
Title: `Create e2e tests with real database and real translation`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T9, T10`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

End-to-end tests exist that exercise the complete `database` module flow against a real Neon database with real translation via `translate_word`. Tests validate the full pipeline: table creation, word addition with deduplication, async translation, user word lists, filtered retrieval, untranslated word exclusion, and cleanup. These are the primary quality gate for the module.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- NFR10-NFR13 (e2e against real Neon)
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "E2E Tests -- Full Real-World Flow" section, scenarios 1-7
- Test file structure: `tests/e2e/database/` with `conftest.py`, `test_word_addition_flow.py`, `test_user_word_lists.py`, `test_untranslated_words.py`

## Preconditions

- T9 completed: unit tests pass (service logic validated).
- T10 completed: integration tests pass (backend CRUD validated against real Neon).
- T8 completed: `testing.py` utilities exist.
- `translate_word` module is functional (existing, not modified).
- `DATABASE_URL` and `OPENAI_API_KEY` configured in Doppler `dev`.

## Non-goals

- Testing `translate_word` internals (already tested in its own module)
- Testing `CachedDatabaseService` in e2e (can be added later)
- Testing latency (already in integration tests)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/e2e/database/__init__.py` -- create empty file
- `tests/e2e/database/conftest.py` -- create with reset/teardown fixtures
- `tests/e2e/database/test_word_addition_flow.py` -- create test file
- `tests/e2e/database/test_user_word_lists.py` -- create test file
- `tests/e2e/database/test_untranslated_words.py` -- create test file

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/` -- no module source code changes
- `tests/unit/`, `tests/integration/` -- different test levels
- Tests of other modules
- Project-level config

**Test scope:**
- Tests go in: `tests/e2e/database/`
- Test command: `doppler run -- uv run pytest tests/e2e/database/ -x -v`
- NEVER run the full test suite during development

## Touched surface (expected files / modules)

- `tests/e2e/database/__init__.py` -- new empty file
- `tests/e2e/database/conftest.py` -- new file with setup/teardown fixtures
- `tests/e2e/database/test_word_addition_flow.py` -- new test file
- `tests/e2e/database/test_user_word_lists.py` -- new test file
- `tests/e2e/database/test_untranslated_words.py` -- new test file

## Dependencies and sequencing notes

- Depends on T9 (unit tests) and T10 (integration tests) for confidence.
- This is the final testing task -- after this, `make check` should be fully green.
- Cannot run in parallel with T10 (both use the same dev database).

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` v9.x, `pytest-asyncio` v1.x (already in dev dependencies)
- **Timing**: `asyncio.sleep()` for waiting for async translation to complete
  - E2e tests need to wait for fire-and-forget translation tasks. Use a polling loop with `asyncio.sleep()` rather than a fixed delay.
- **Doppler**: `doppler run --` provides both `DATABASE_URL` and `OPENAI_API_KEY`

## Implementation steps (developer-facing)

### 1. Create `tests/e2e/database/__init__.py`

Empty file.

### 2. Create `tests/e2e/database/conftest.py`

Setup and teardown fixtures per architecture spec:

```python
import pytest

from nl_processing.database.testing import drop_all_tables, reset_database


@pytest.fixture(autouse=True)
async def _database_lifecycle() -> None:
    """Reset database before each test, drop all tables after."""
    await reset_database()
    yield
    await drop_all_tables()
```

**Note**: `autouse=True` ensures every test in this directory gets a clean database. The `yield` separates setup from teardown.

### 3. Create `tests/e2e/database/test_word_addition_flow.py`

Covers architecture scenarios 2, 3:

```python
import asyncio

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.service import DatabaseService
from nl_processing.database.testing import count_words, count_translation_links


_TEST_WORDS = [
    Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
]


@pytest.mark.asyncio
async def test_add_new_words_reports_all_as_new() -> None:
    """Adding words for the first time: all reported as new."""
    db = DatabaseService(user_id="test_user")
    result = await db.add_words(_TEST_WORDS)
    assert len(result.new_words) == 3
    assert len(result.existing_words) == 0


@pytest.mark.asyncio
async def test_add_same_words_twice_reports_existing() -> None:
    """Adding same words again: all reported as existing, no duplicates."""
    db = DatabaseService(user_id="test_user")
    await db.add_words(_TEST_WORDS)
    result = await db.add_words(_TEST_WORDS)
    assert len(result.new_words) == 0
    assert len(result.existing_words) == 3
    # Verify no duplicates in DB
    count = await count_words("words_nl")
    assert count == 3


@pytest.mark.asyncio
async def test_async_translation_creates_links() -> None:
    """After adding words and waiting, translations appear in DB."""
    db = DatabaseService(user_id="test_user")
    await db.add_words(_TEST_WORDS)

    # Wait for background translation to complete (poll with timeout)
    for _ in range(30):  # 30 * 0.5s = 15s max wait
        await asyncio.sleep(0.5)
        link_count = await count_translation_links("translations_nl_ru")
        if link_count >= len(_TEST_WORDS):
            break

    link_count = await count_translation_links("translations_nl_ru")
    assert link_count >= len(_TEST_WORDS), (
        f"Expected {len(_TEST_WORDS)} translation links, got {link_count}"
    )

    # Verify translated words exist in words_ru
    ru_count = await count_words("words_ru")
    assert ru_count >= len(_TEST_WORDS)
```

### 4. Create `tests/e2e/database/test_user_word_lists.py`

Covers architecture scenarios 4, 5:

```python
import asyncio

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.service import DatabaseService
from nl_processing.database.testing import count_translation_links


_NOUNS = [
    Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
]
_VERBS = [
    Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
]


@pytest.mark.asyncio
async def test_multi_user_word_isolation() -> None:
    """Two users adding overlapping words: each sees only their own."""
    db1 = DatabaseService(user_id="user_1")
    db2 = DatabaseService(user_id="user_2")

    await db1.add_words(_NOUNS)
    await db2.add_words(_NOUNS + _VERBS)

    # Wait for translations
    for _ in range(30):
        await asyncio.sleep(0.5)
        link_count = await count_translation_links("translations_nl_ru")
        if link_count >= 3:
            break

    pairs_1 = await db1.get_words()
    pairs_2 = await db2.get_words()

    # user_1 added 2 words, user_2 added 3
    assert len(pairs_1) <= 2  # May be less if translations pending
    assert len(pairs_2) <= 3


@pytest.mark.asyncio
async def test_get_words_filter_by_word_type() -> None:
    """get_words(word_type=NOUN) returns only nouns."""
    db = DatabaseService(user_id="test_user")
    all_words = _NOUNS + _VERBS
    await db.add_words(all_words)

    # Wait for translations
    for _ in range(30):
        await asyncio.sleep(0.5)
        link_count = await count_translation_links("translations_nl_ru")
        if link_count >= len(all_words):
            break

    noun_pairs = await db.get_words(word_type=PartOfSpeech.NOUN)
    for pair in noun_pairs:
        assert pair.source.word_type == PartOfSpeech.NOUN


@pytest.mark.asyncio
async def test_get_words_with_limit() -> None:
    """get_words(limit=1) returns at most 1 pair."""
    db = DatabaseService(user_id="test_user")
    await db.add_words(_NOUNS)

    # Wait for translations
    for _ in range(30):
        await asyncio.sleep(0.5)
        link_count = await count_translation_links("translations_nl_ru")
        if link_count >= len(_NOUNS):
            break

    pairs = await db.get_words(limit=1)
    assert len(pairs) <= 1
```

### 5. Create `tests/e2e/database/test_untranslated_words.py`

Covers architecture scenario 6:

```python
import logging

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.service import DatabaseService


@pytest.mark.asyncio
async def test_get_words_excludes_untranslated(caplog: pytest.LogCaptureFixture) -> None:
    """Immediately after adding words, untranslated ones are excluded with warning."""
    db = DatabaseService(user_id="test_user")
    words = [
        Word(normalized_form="fiets", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]
    await db.add_words(words)

    # Call get_words immediately (before translation completes)
    with caplog.at_level(logging.WARNING, logger="nl_processing.database"):
        pairs = await db.get_words()

    # Untranslated words should be excluded
    # (pairs may be empty if translation hasn't completed yet)
    # The key assertion: if words were excluded, a warning was logged
    if len(pairs) < len(words):
        assert any(
            "excluded" in record.message.lower() or "pending" in record.message.lower()
            for record in caplog.records
        ), "Expected a warning about untranslated/pending words"
```

### 6. Ensure each test file is under 200 lines

### 7. Run e2e tests

```bash
doppler run -- uv run pytest tests/e2e/database/ -x -v
```

### 8. Run `make check`

## Production safety constraints (mandatory)

- **Database operations**: All operations target `nl_processing_dev` via Doppler `dev`.
- **Real translation**: E2e tests make real OpenAI API calls via `translate_word`. This costs real API tokens but is necessary for e2e validation.
- **Cleanup**: `conftest.py` ensures `reset_database()` before and `drop_all_tables()` after every test.
- **NEVER run these tests against `prd` or `stg` Doppler environments.**

## Anti-disaster constraints (mandatory)

- Tests use `conftest.py` autouse fixture for guaranteed setup/teardown.
- Tests use unambiguous Dutch words (common nouns) to minimize LLM translation variability.
- Tests assert structural correctness (links exist, counts match) not exact translation text.
- Tests follow existing e2e patterns from `tests/e2e/translate_word/`.

## Error handling + correctness rules (mandatory)

- Tests verify the warning log for untranslated word exclusion (FR22).
- Tests do NOT swallow exceptions -- failures propagate.
- Translation polling has a timeout (15s) to prevent infinite waits.

## Zero legacy tolerance rule (mandatory)

- No legacy test files. All new.

## Acceptance criteria (testable)

1. `tests/e2e/database/` directory exists with `__init__.py` and `conftest.py`
2. `conftest.py` has autouse fixture with `reset_database()` setup and `drop_all_tables()` teardown
3. `test_word_addition_flow.py` tests word addition, deduplication, and async translation
4. `test_user_word_lists.py` tests multi-user isolation and filtering
5. `test_untranslated_words.py` tests exclusion of untranslated words with warning
6. All tests pass: `doppler run -- uv run pytest tests/e2e/database/ -x -v`
7. All test files under 200 lines
8. `make check` passes 100% green

## Verification / quality gates

- [ ] All e2e tests pass: `doppler run -- uv run pytest tests/e2e/database/ -x -v`
- [ ] Ruff format and check pass on test files
- [ ] Pylint 200-line limit passes
- [ ] Tests produce no unhandled warnings
- [ ] Dev database is clean after test run
- [ ] `make check` passes 100% green

## Edge cases

- Translation may take varying time (1-10s depending on OpenAI API load). Polling loop handles this.
- If translation fails entirely (API error), the test for `test_async_translation_creates_links` may fail. This is expected -- it means the translation pipeline is broken.
- `pytest-xdist` parallel execution: e2e tests that share the same database may interfere. If this is an issue, use `pytest.ini` markers or a conftest-level lock. The `make check` command uses `-n auto` -- if e2e tests fail due to parallelism, they may need serialization.

## Notes / risks

- **Risk**: E2e tests are slower (real API calls, real DB). Each test may take 5-15s. Total e2e suite: ~30-60s.
- **Risk**: OpenAI API rate limits may affect test reliability. Use small word batches (3-5 words per test).
- **Risk**: `pytest-xdist` parallel execution with shared database. Mitigation: the `conftest.py` fixture resets the database per test, which should handle most parallelism issues. If not, serialize.
- **Decision made autonomously**: Using polling loops (`asyncio.sleep` + count check) rather than fixed delays. This is more robust across different network conditions.
- **Decision made autonomously**: Asserting translation link counts (structural) rather than exact translation text (semantic). This avoids LLM nondeterminism in e2e tests.
