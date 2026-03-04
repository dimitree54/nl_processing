---
Task ID: `T5`
Title: `Implement NeonBackend in backend/neon.py using asyncpg`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T4`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

A concrete `NeonBackend` class exists that implements `AbstractBackend` using `asyncpg` to connect to Neon PostgreSQL. All 6 abstract methods are implemented with proper SQL queries, connection pooling, and error handling. The backend is the data access layer that `DatabaseService` (T6) delegates to.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- FR1-FR4 (table creation), FR6 (dedup by normalized_form), NFR1 (200ms latency), NFR8-NFR9 (error handling, connection pooling), NFR15 (asyncpg)
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Neon PostgreSQL as First Backend", table schemas, "Abstract Backend Interface"

## Preconditions

- T4 completed: `AbstractBackend` ABC exists.
- T2 completed: `asyncpg` installed, `DATABASE_URL` configured in Doppler.

## Non-goals

- `DatabaseService` logic (Word model conversion, translation triggering) -- that's T6
- Caching -- that's T7
- Tests -- that's T9-T11

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/backend/neon.py` -- create new file

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/database/service.py` -- not yet
- `nl_processing/database/backend/abstract.py` -- already created in T4
- Any test files
- Other modules

**Test scope:**
- No automated tests in this task. Manual connectivity verification via REPL.
- Formal testing in T10 (integration tests).

## Touched surface (expected files / modules)

- `nl_processing/database/backend/neon.py` -- new file

## Dependencies and sequencing notes

- Depends on T4 for `AbstractBackend` interface.
- T6 depends on this for the concrete backend.
- T10 depends on this for integration testing.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncpg` v0.31.0
  - **Connection pools**: https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.pool.create_pool
    - `asyncpg.create_pool(dsn, min_size=1, max_size=10)` -- creates a connection pool
    - `pool.acquire()` -- async context manager to borrow a connection
    - `pool.close()` -- close all connections in the pool
  - **Query methods**:
    - `conn.execute(query, *args)` -- execute DDL/DML, returns status string
    - `conn.fetch(query, *args)` -- returns `list[Record]`
    - `conn.fetchrow(query, *args)` -- returns `Record | None`
    - `conn.fetchval(query, *args)` -- returns scalar value
  - **Parameter placeholders**: `$1, $2, $3` (PostgreSQL native, not `%s`)
  - **Record objects**: `asyncpg.Record` supports dict-like access: `record['column_name']`
  - **Error types**: `asyncpg.PostgresError` base, `asyncpg.UniqueViolationError` for UNIQUE constraint violations
  - **Known gotcha**: Neon requires SSL. The DSN from Neon console includes `sslmode=require`.
  - **Known gotcha**: `asyncpg.create_pool()` is a coroutine -- must be awaited.

## Implementation steps (developer-facing)

### 1. Create `nl_processing/database/backend/neon.py`

```python
import os

import asyncpg

from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.exceptions import ConfigurationError, DatabaseError
from nl_processing.database.logging import get_logger

_logger = get_logger("neon")


class NeonBackend(AbstractBackend):
    """Neon PostgreSQL backend using asyncpg connection pool."""

    def __init__(self) -> None:
        try:
            self._dsn = os.environ["DATABASE_URL"]
        except KeyError:
            msg = (
                "DATABASE_URL environment variable is required. "
                "Set it to your Neon PostgreSQL connection string. "
                "Example: postgresql://user:pass@host/dbname?sslmode=require"
            )
            raise ConfigurationError(msg)
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        """Lazy-initialize and return the connection pool."""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(
                    self._dsn, min_size=1, max_size=5
                )
            except Exception as exc:
                raise DatabaseError(f"Failed to create connection pool: {exc}") from exc
        return self._pool
    ...
```

### 2. Implement `create_tables`

```python
async def create_tables(
    self, languages: list[str], pairs: list[tuple[str, str]]
) -> None:
    pool = await self._get_pool()
    async with pool.acquire() as conn:
        # Per-language word tables
        for lang in languages:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS words_{lang} (
                    id SERIAL PRIMARY KEY,
                    normalized_form VARCHAR NOT NULL UNIQUE,
                    word_type VARCHAR NOT NULL
                )
            """)
        # Per-language-pair translation link tables
        for src, tgt in pairs:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS translations_{src}_{tgt} (
                    id SERIAL PRIMARY KEY,
                    source_word_id INTEGER NOT NULL
                        REFERENCES words_{src}(id),
                    target_word_id INTEGER NOT NULL
                        REFERENCES words_{tgt}(id),
                    UNIQUE(source_word_id, target_word_id)
                )
            """)
        # User words table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_words (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                word_id INTEGER NOT NULL,
                language VARCHAR NOT NULL,
                added_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, word_id, language)
            )
        """)
    _logger.info("Tables created for languages=%s, pairs=%s", languages, pairs)
```

### 3. Implement `add_word`

Use `INSERT ... ON CONFLICT DO NOTHING RETURNING id` to handle deduplication:

```python
async def add_word(
    self, table: str, normalized_form: str, word_type: str
) -> int | None:
    pool = await self._get_pool()
    async with pool.acquire() as conn:
        row_id = await conn.fetchval(
            f"INSERT INTO {table} (normalized_form, word_type) "
            f"VALUES ($1, $2) ON CONFLICT (normalized_form) DO NOTHING "
            f"RETURNING id",
            normalized_form, word_type,
        )
        return row_id  # None if already existed
```

### 4. Implement `get_word`

```python
async def get_word(
    self, table: str, normalized_form: str
) -> dict | None:
    pool = await self._get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT id, normalized_form, word_type FROM {table} "
            f"WHERE normalized_form = $1",
            normalized_form,
        )
        if row is None:
            return None
        return dict(row)
```

### 5. Implement `add_translation_link`

```python
async def add_translation_link(
    self, table: str, source_id: int, target_id: int
) -> None:
    pool = await self._get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            f"INSERT INTO {table} (source_word_id, target_word_id) "
            f"VALUES ($1, $2) ON CONFLICT DO NOTHING",
            source_id, target_id,
        )
```

### 6. Implement `add_user_word`

```python
async def add_user_word(
    self, user_id: str, word_id: int, language: str
) -> None:
    pool = await self._get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO user_words (user_id, word_id, language) "
            "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            user_id, word_id, language,
        )
```

### 7. Implement `get_user_words`

This method builds a query that joins `user_words` with the language word table and the translation link table to return only words that have translations. Supports filtering by `word_type`, `limit`, and `random`:

```python
async def get_user_words(
    self, user_id: str, language: str, **filters: object
) -> list[dict]:
    pool = await self._get_pool()
    word_type = filters.get("word_type")
    limit = filters.get("limit")
    random_order = filters.get("random", False)

    query = (
        f"SELECT w.id, w.normalized_form, w.word_type "
        f"FROM user_words uw "
        f"JOIN words_{language} w ON uw.word_id = w.id "
        f"WHERE uw.user_id = $1 AND uw.language = $2"
    )
    args: list[object] = [user_id, language]

    if word_type is not None:
        args.append(str(word_type))
        query += f" AND w.word_type = ${len(args)}"

    if random_order:
        query += " ORDER BY RANDOM()"

    if limit is not None:
        args.append(int(limit))  # type: ignore[arg-type]
        query += f" LIMIT ${len(args)}"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
    return [dict(row) for row in rows]
```

### 8. Wrap all database operations in try/except for DatabaseError

Each method should wrap `asyncpg` exceptions:

```python
try:
    # ... database operation ...
except asyncpg.PostgresError as exc:
    raise DatabaseError(f"Database operation failed: {exc}") from exc
```

The exact placement depends on the final code structure. Do NOT use blanket `except Exception` -- only catch `asyncpg.PostgresError` and re-raise as `DatabaseError`.

### 9. Ensure file is under 200 lines

If the file approaches 200 lines, consider:
- Moving table-name construction helpers to a small private function
- Keeping docstrings concise

### 10. Run `make check`

- Ruff format/check must pass
- Pylint 200-line limit must pass
- `make check` must be 100% green

## Production safety constraints (mandatory)

- **Database operations**: No database operations run during this task (code only). The backend reads `DATABASE_URL` from environment at instantiation time.
- **Resource isolation**: The `DATABASE_URL` comes from Doppler `dev` environment, pointing to `nl_processing_dev`. Production database is never accessed.

## Anti-disaster constraints (mandatory)

- `asyncpg` is the architecture-approved library (NFR15).
- Connection pooling (`create_pool`) handles connection reuse and limits (NFR9).
- Table names are constructed from trusted language codes, not user input. However, they use f-strings in SQL -- this is acceptable because the language codes come from the `Language` enum (a closed set), not from external input.
- Uses `os.environ['DATABASE_URL']` (not `os.getenv()`) per project convention.

## Error handling + correctness rules (mandatory)

- `ConfigurationError` raised at `__init__` if `DATABASE_URL` is missing (FR17).
- `DatabaseError` raised for all `asyncpg.PostgresError` exceptions (NFR8).
- `ON CONFLICT DO NOTHING` for deduplication -- no errors raised for duplicates (FR6).
- No empty catch blocks. No blanket exception swallowing.

## Zero legacy tolerance rule (mandatory)

- No legacy code affected. This is a new file.

## Acceptance criteria (testable)

1. `nl_processing/database/backend/neon.py` exists with `NeonBackend` class
2. `NeonBackend` extends `AbstractBackend` and implements all 6 methods
3. Constructor reads `DATABASE_URL` from `os.environ[]` and raises `ConfigurationError` if missing
4. Lazy connection pool initialization via `_get_pool()`
5. `create_tables` uses `IF NOT EXISTS` for all tables (FR27)
6. `add_word` uses `ON CONFLICT DO NOTHING RETURNING id` for dedup (FR6)
7. `add_user_word` uses `ON CONFLICT DO NOTHING` for idempotency
8. `get_user_words` supports `word_type`, `limit`, `random` filters
9. All `asyncpg.PostgresError` exceptions wrapped as `DatabaseError`
10. File under 200 lines
11. `make check` passes 100% green

## Verification / quality gates

- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] Import works: `from nl_processing.database.backend.neon import NeonBackend`
- [ ] `NeonBackend()` raises `ConfigurationError` when `DATABASE_URL` not set
- [ ] `make check` passes 100% green

## Edge cases

- Neon cold start: first `_get_pool()` call may take 100-300ms. Subsequent calls use the cached pool.
- Empty `languages` or `pairs` list in `create_tables`: should still create the `user_words` table.
- `get_user_words` with no filters: returns all user words without WHERE clause additions.
- `get_user_words` with `random=True` and no `limit`: returns all words in random order.
- `add_word` with a word that already exists: returns `None` (not an error).

## Notes / risks

- **Decision made autonomously**: Pool size `min_size=1, max_size=5`. This is conservative and appropriate for a dev/test environment. Can be tuned later.
- **Decision made autonomously**: Using f-strings for table names in SQL. This is safe because table names are derived from `Language` enum values (a closed set), never from user input.
- **Risk**: If `neon.py` exceeds 200 lines, split helper functions (e.g., query builders) into a private module. Monitor during implementation.
