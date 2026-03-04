---
Task ID: `T10`
Title: `Create integration tests against real Neon PostgreSQL`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T8`
Parallelizable: `yes, with T9`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Integration tests exist that validate `NeonBackend` and `DatabaseService` against a real Neon PostgreSQL database. Tests cover table creation, word CRUD with deduplication, translation link creation, user word lists, and a latency benchmark (p95 <= 200ms for 50 operations). These tests use the `dev` Doppler environment and the `testing.py` utilities for setup/teardown.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- NFR1 (200ms latency), NFR10-NFR14 (testing against real Neon)
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Integration Tests" section, "Doppler Environment Strategy for Testing"
- Test file structure: `tests/integration/database/` with `test_neon_backend.py`, `test_table_creation.py`, `test_latency.py`

## Preconditions

- T8 completed: `testing.py` utilities exist (`reset_database`, `drop_all_tables`, count helpers).
- T5 completed: `NeonBackend` exists.
- T2 completed: `DATABASE_URL` configured in Doppler `dev`.

## Non-goals

- E2e tests (T11)
- Testing translation (integration tests don't call `translate_word`)
- Testing `CachedDatabaseService`

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/integration/database/__init__.py` -- create empty file
- `tests/integration/database/test_neon_backend.py` -- create test file
- `tests/integration/database/test_table_creation.py` -- create test file
- `tests/integration/database/test_latency.py` -- create test file

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/` -- no module source code changes
- `tests/unit/`, `tests/e2e/` -- different test levels
- Tests of other modules
- Project-level config

**Test scope:**
- Tests go in: `tests/integration/database/`
- Test command: `doppler run -- uv run pytest tests/integration/database/ -x -v`
- NEVER run the full test suite during development

## Touched surface (expected files / modules)

- `tests/integration/database/__init__.py` -- new empty file
- `tests/integration/database/test_neon_backend.py` -- new test file
- `tests/integration/database/test_table_creation.py` -- new test file
- `tests/integration/database/test_latency.py` -- new test file

## Dependencies and sequencing notes

- Depends on T8 for `testing.py` utilities.
- T11 depends on this for integration test confidence.
- Can run in parallel with T9 (unit tests).

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` v9.x, `pytest-asyncio` v1.x (already in dev dependencies)
- **Doppler CLI**: `doppler run --` prefix provides `DATABASE_URL` environment variable
  - Docs: https://docs.doppler.com/docs/cli
  - Usage: `doppler run -- uv run pytest tests/integration/database/ -x -v`
- **Latency measurement**: Python `time.time()` for wall-clock timing (same pattern as `tests/integration/translate_word/test_translation_accuracy.py`)

## Implementation steps (developer-facing)

### 1. Create `tests/integration/database/__init__.py`

Empty file.

### 2. Create `tests/integration/database/test_table_creation.py`

Tests for `create_tables` and `drop_all_tables`:

```python
import pytest

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.testing import drop_all_tables, reset_database


@pytest.mark.asyncio
async def test_create_tables_creates_all_required_tables() -> None:
    """create_tables() creates words_nl, words_ru, translations_nl_ru, user_words."""
    await reset_database()
    backend = NeonBackend()
    pool = await backend._get_pool()
    async with pool.acquire() as conn:
        # Check tables exist by querying information_schema
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name IN "
            "('words_nl', 'words_ru', 'translations_nl_ru', 'user_words')"
        )
        table_names = {row["table_name"] for row in tables}
    assert table_names == {"words_nl", "words_ru", "translations_nl_ru", "user_words"}
    await drop_all_tables()


@pytest.mark.asyncio
async def test_create_tables_is_idempotent() -> None:
    """Calling create_tables() twice does not raise errors (IF NOT EXISTS)."""
    await reset_database()
    backend = NeonBackend()
    await backend.create_tables(["nl", "ru"], [("nl", "ru")])  # Second call
    await drop_all_tables()


@pytest.mark.asyncio
async def test_drop_all_tables_removes_everything() -> None:
    """drop_all_tables() removes all module tables."""
    await reset_database()
    await drop_all_tables()
    backend = NeonBackend()
    pool = await backend._get_pool()
    async with pool.acquire() as conn:
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name IN "
            "('words_nl', 'words_ru', 'translations_nl_ru', 'user_words')"
        )
    assert len(tables) == 0
```

### 3. Create `tests/integration/database/test_neon_backend.py`

Tests for `NeonBackend` CRUD operations:

```python
import pytest

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.testing import (
    count_words,
    count_translation_links,
    count_user_words,
    drop_all_tables,
    reset_database,
)


@pytest.mark.asyncio
async def test_add_word_returns_id_for_new_word() -> None:
    await reset_database()
    backend = NeonBackend()
    row_id = await backend.add_word("words_nl", "huis", "noun")
    assert row_id is not None
    assert isinstance(row_id, int)
    await drop_all_tables()


@pytest.mark.asyncio
async def test_add_word_returns_none_for_duplicate() -> None:
    await reset_database()
    backend = NeonBackend()
    await backend.add_word("words_nl", "huis", "noun")
    row_id = await backend.add_word("words_nl", "huis", "noun")
    assert row_id is None
    await drop_all_tables()


@pytest.mark.asyncio
async def test_get_word_returns_dict_for_existing() -> None:
    await reset_database()
    backend = NeonBackend()
    await backend.add_word("words_nl", "huis", "noun")
    word = await backend.get_word("words_nl", "huis")
    assert word is not None
    assert word["normalized_form"] == "huis"
    assert word["word_type"] == "noun"
    assert "id" in word
    await drop_all_tables()


@pytest.mark.asyncio
async def test_get_word_returns_none_for_nonexistent() -> None:
    await reset_database()
    backend = NeonBackend()
    word = await backend.get_word("words_nl", "nonexistent")
    assert word is None
    await drop_all_tables()


@pytest.mark.asyncio
async def test_add_translation_link_creates_link() -> None:
    await reset_database()
    backend = NeonBackend()
    src_id = await backend.add_word("words_nl", "huis", "noun")
    tgt_id = await backend.add_word("words_ru", "дом", "noun")
    await backend.add_translation_link("translations_nl_ru", src_id, tgt_id)
    count = await count_translation_links("translations_nl_ru")
    assert count == 1
    await drop_all_tables()


@pytest.mark.asyncio
async def test_add_user_word_creates_association() -> None:
    await reset_database()
    backend = NeonBackend()
    word_id = await backend.add_word("words_nl", "huis", "noun")
    await backend.add_user_word("test_user", word_id, "nl")
    count = await count_user_words("test_user", "nl")
    assert count == 1
    await drop_all_tables()


@pytest.mark.asyncio
async def test_add_user_word_idempotent() -> None:
    await reset_database()
    backend = NeonBackend()
    word_id = await backend.add_word("words_nl", "huis", "noun")
    await backend.add_user_word("test_user", word_id, "nl")
    await backend.add_user_word("test_user", word_id, "nl")  # Duplicate
    count = await count_user_words("test_user", "nl")
    assert count == 1  # Still 1, not 2
    await drop_all_tables()


@pytest.mark.asyncio
async def test_deduplication_no_duplicate_words() -> None:
    await reset_database()
    backend = NeonBackend()
    await backend.add_word("words_nl", "huis", "noun")
    await backend.add_word("words_nl", "huis", "noun")
    count = await count_words("words_nl")
    assert count == 1
    await drop_all_tables()
```

### 4. Create `tests/integration/database/test_latency.py`

Latency benchmark (NFR1, NFR14):

```python
import time

import pytest

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.testing import drop_all_tables, reset_database


@pytest.mark.asyncio
async def test_add_word_latency_p95_under_200ms() -> None:
    """p95 of 50 add_word operations must be <= 200ms (NFR1, NFR14)."""
    await reset_database()
    backend = NeonBackend()

    timings: list[float] = []
    for i in range(50):
        start = time.time()
        await backend.add_word("words_nl", f"testword_{i}", "noun")
        elapsed = time.time() - start
        timings.append(elapsed)

    timings.sort()
    p95_index = int(len(timings) * 0.95) - 1
    p95 = timings[p95_index]

    assert p95 <= 0.2, (
        f"p95 latency is {p95:.3f}s -- exceeds 200ms threshold. "
        f"Timings: min={timings[0]:.3f}s, median={timings[24]:.3f}s, "
        f"max={timings[-1]:.3f}s"
    )
    await drop_all_tables()
```

### 5. Ensure each test file is under 200 lines

### 6. Run integration tests

```bash
doppler run -- uv run pytest tests/integration/database/ -x -v
```

### 7. Run `make check`

## Production safety constraints (mandatory)

- **Database operations**: All operations target the dev Neon database (`nl_processing_dev`) via Doppler `dev` environment.
- **Resource isolation**: `DATABASE_URL` from Doppler `dev` -- never `prd` or `stg`.
- **Cleanup**: Every test calls `reset_database()` in setup and `drop_all_tables()` in teardown. Dev database is always left clean.

## Anti-disaster constraints (mandatory)

- Tests follow existing integration test patterns from `tests/integration/translate_word/`.
- Each test is self-contained: setup, action, assert, teardown.
- No shared state between tests.

## Error handling + correctness rules (mandatory)

- Tests verify error cases: `ConfigurationError` for missing env var, `None` return for nonexistent words.
- Tests do NOT swallow exceptions -- any unexpected error fails the test.
- Latency test produces a clear error message with timing details if threshold exceeded.

## Zero legacy tolerance rule (mandatory)

- No legacy test files. All new.

## Acceptance criteria (testable)

1. `tests/integration/database/` directory exists with `__init__.py`
2. `test_table_creation.py` tests `create_tables` and `drop_all_tables` against real Neon
3. `test_neon_backend.py` tests all backend CRUD operations against real Neon
4. `test_latency.py` benchmarks p95 of 50 operations <= 200ms
5. All tests use `reset_database()`/`drop_all_tables()` for setup/teardown
6. All tests pass: `doppler run -- uv run pytest tests/integration/database/ -x -v`
7. All test files under 200 lines
8. `make check` passes 100% green

## Verification / quality gates

- [ ] All integration tests pass: `doppler run -- uv run pytest tests/integration/database/ -x -v`
- [ ] Ruff format and check pass on test files
- [ ] Pylint 200-line limit passes
- [ ] Latency benchmark passes (p95 <= 200ms)
- [ ] Dev database is clean after test run
- [ ] `make check` passes 100% green

## Edge cases

- Neon cold start may affect first test's latency. The latency benchmark uses 50 operations, so the cold start is amortized.
- Network issues during tests: `asyncpg` raises exceptions which fail the test (expected behavior).
- Parallel test execution (`pytest-xdist`): tests must not share database state. Each test resets the database.

## Notes / risks

- **Risk**: Neon cold start latency may cause the first few operations to exceed 200ms. The p95 metric across 50 operations should absorb this. If the benchmark still fails, consider warming up the connection pool before the timing loop.
- **Risk**: `pytest-xdist` parallel execution may cause test interference (multiple tests resetting the database simultaneously). If this occurs, add `@pytest.mark.serial` or use a shared fixture. For now, `-n auto` is used by `make check` -- if tests fail due to parallelism, serialize the database integration tests.
- **Decision made autonomously**: Using inline `reset_database()`/`drop_all_tables()` calls in each test rather than fixtures. This makes each test fully self-contained and avoids fixture ordering issues.
