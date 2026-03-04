---
Task ID: `T8`
Title: `Create testing.py with drop_all_tables, reset_database, and count helpers`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T6`
Parallelizable: `yes, with T9, T12`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Test utility functions exist in `testing.py` for use by integration and e2e tests. These functions enable clean database state management: dropping all tables, resetting the database, and counting rows for assertions. They are NOT production code -- they are imported only by test files.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- FR23-FR26 (testing utilities)
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Backdoor / Test Utility Functions" section, full function signatures

## Preconditions

- T6 completed: `DatabaseService` exists (needed for `create_tables` delegation in `reset_database`).
- T5 completed: `NeonBackend` exists (used by testing utilities for direct DB access).

## Non-goals

- Production code changes
- Actual test creation (T9-T11)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/testing.py` -- create new file

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/database/service.py` -- already created
- `nl_processing/database/backend/` -- already created
- Any test files (those come in T9-T11)
- Other modules

**Test scope:**
- No automated tests in this task. The utilities ARE for tests (T10, T11).

## Touched surface (expected files / modules)

- `nl_processing/database/testing.py` -- new file

## Dependencies and sequencing notes

- Depends on T6 for `DatabaseService` (used by `reset_database`).
- T10 (integration tests) and T11 (e2e tests) depend on these utilities.
- Can run in parallel with T9 and T12 (after T6).

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncpg` (already installed in T2)
  - `conn.fetchval("SELECT COUNT(*) FROM table")` -- count rows
  - `conn.execute("DROP TABLE IF EXISTS table CASCADE")` -- drop tables
- No new dependencies.

## Implementation steps (developer-facing)

### 1. Create `nl_processing/database/testing.py`

```python
"""Test utilities for the database module.

NOT for production use. Imported only by test files.
These functions operate against the DATABASE_URL environment variable
and use the same NeonBackend as production code.
"""

from nl_processing.core.models import Language
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.logging import get_logger

_logger = get_logger("testing")

_LANGUAGES = [Language.NL.value, Language.RU.value]
_PAIRS = [(Language.NL.value, Language.RU.value)]


async def drop_all_tables() -> None:
    """Drop all module-managed tables. Irreversible.

    Drops: words_{lang} for each language, translations_{src}_{tgt}
    for each pair, and user_words.
    """
    backend = NeonBackend()
    pool = await backend._get_pool()
    async with pool.acquire() as conn:
        # Drop in reverse dependency order (links first, then words)
        for src, tgt in _PAIRS:
            await conn.execute(
                f"DROP TABLE IF EXISTS translations_{src}_{tgt} CASCADE"
            )
        await conn.execute("DROP TABLE IF EXISTS user_words CASCADE")
        for lang in _LANGUAGES:
            await conn.execute(f"DROP TABLE IF EXISTS words_{lang} CASCADE")
    _logger.info("All tables dropped")


async def reset_database() -> None:
    """Drop all tables and recreate them empty.

    Equivalent to drop_all_tables() + DatabaseService.create_tables().
    """
    await drop_all_tables()
    backend = NeonBackend()
    await backend.create_tables(_LANGUAGES, _PAIRS)
    _logger.info("Database reset complete")


async def count_words(table: str) -> int:
    """Return the number of rows in a word table.

    Args:
        table: Table name (e.g., "words_nl", "words_ru").
    """
    backend = NeonBackend()
    pool = await backend._get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
    return int(count)


async def count_user_words(user_id: str, language: str) -> int:
    """Return the number of words associated with a user.

    Args:
        user_id: The user identifier.
        language: Language code (e.g., "nl", "ru").
    """
    backend = NeonBackend()
    pool = await backend._get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM user_words "
            "WHERE user_id = $1 AND language = $2",
            user_id, language,
        )
    return int(count)


async def count_translation_links(table: str) -> int:
    """Return the number of translation links.

    Args:
        table: Link table name (e.g., "translations_nl_ru").
    """
    backend = NeonBackend()
    pool = await backend._get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
    return int(count)
```

### 2. Key design decisions

- Each function creates its own `NeonBackend` instance. This keeps functions stateless and independently callable.
- `drop_all_tables` drops in reverse dependency order: translation links first, then user_words, then word tables. This respects foreign key constraints.
- `reset_database` calls `drop_all_tables` then `backend.create_tables()` directly (not `DatabaseService.create_tables()`) to avoid unnecessary object construction.
- `_LANGUAGES` and `_PAIRS` are duplicated from `DatabaseService` -- this avoids importing `DatabaseService` (which would pull in `translate_word` dependencies just for testing utilities).
- Table names use f-strings with known language codes (same safe pattern as `NeonBackend`).

### 3. Verify file is under 200 lines

### 4. Run `make check`

## Production safety constraints (mandatory)

- **These functions are destructive** (`drop_all_tables` is irreversible). They must ONLY be called against the dev database.
- **Resource isolation**: Functions use `DATABASE_URL` from the environment. In dev/test context (via Doppler `dev`), this points to `nl_processing_dev`.
- **NEVER import these functions from production code.** They live in `testing.py` specifically to signal they are test-only.

## Anti-disaster constraints (mandatory)

- Functions match the architecture spec signatures exactly.
- `DROP TABLE IF EXISTS ... CASCADE` ensures no errors if tables don't exist.
- No new dependencies.

## Error handling + correctness rules (mandatory)

- Database errors propagate as-is (from `asyncpg`). Test utilities don't wrap errors -- tests should see the raw failure.
- No empty catch blocks.

## Zero legacy tolerance rule (mandatory)

- No legacy code affected. New file.

## Acceptance criteria (testable)

1. `nl_processing/database/testing.py` exists with all 5 functions
2. `drop_all_tables()` drops all tables in correct order (FK-safe)
3. `reset_database()` drops and recreates all tables
4. `count_words(table)` returns row count for a word table
5. `count_user_words(user_id, language)` returns user-word association count
6. `count_translation_links(table)` returns link count
7. All functions are `async def`
8. File under 200 lines
9. `make check` passes 100% green

## Verification / quality gates

- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] Import works: `from nl_processing.database.testing import drop_all_tables, reset_database, count_words`
- [ ] `make check` passes 100% green

## Edge cases

- `drop_all_tables` when tables don't exist: `IF EXISTS` prevents errors.
- `count_words` on a table with 0 rows: returns `0`.
- `reset_database` when tables already exist: drops then recreates cleanly.

## Notes / risks

- **Decision made autonomously**: Each function creates its own `NeonBackend` instance rather than sharing a module-level singleton. This is simpler and avoids state management in a test utility module.
- **Decision made autonomously**: Accessing `backend._get_pool()` directly (private method). This is acceptable because `testing.py` is a test utility, not production code, and the alternative would be adding public pool access to the backend interface.
