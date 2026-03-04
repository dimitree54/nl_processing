---
Task ID: `T4`
Title: `Create AbstractBackend ABC in backend/abstract.py`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T3`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The `AbstractBackend` abstract base class exists, defining the contract for all database backends. This enables the `NeonBackend` (T5) to implement concretely and the `DatabaseService` (T6) to program against the abstraction. Unit tests (T9) can mock this interface.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- implicit in "backend abstraction" (product brief scope item 8)
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Abstract Backend Interface" section, full method signatures

## Preconditions

- T3 completed: `exceptions.py`, `models.py`, `logging.py` exist.

## Non-goals

- Neon implementation (T5)
- Service implementation (T6)
- Tests (T9-T11)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/backend/` -- create directory
- `nl_processing/database/backend/__init__.py` -- create empty file
- `nl_processing/database/backend/abstract.py` -- create new file

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/database/service.py` -- not yet
- `nl_processing/database/exceptions.py`, `models.py`, `logging.py` -- already created in T3
- Any test files
- Other modules

**Test scope:**
- No tests in this task. Verified via import and `make check`.

## Touched surface (expected files / modules)

- `nl_processing/database/backend/__init__.py` -- new empty file
- `nl_processing/database/backend/abstract.py` -- new file

## Dependencies and sequencing notes

- Depends on T3 for foundation types.
- T5 depends on this for the interface to implement.
- T6 depends on this for the interface to program against.

## Third-party / library research (mandatory for any external dependency)

- **Library**: Python `abc` module (stdlib)
  - `ABC`, `abstractmethod` -- standard abstract base class pattern
  - Docs: https://docs.python.org/3/library/abc.html

## Implementation steps (developer-facing)

### 1. Create `nl_processing/database/backend/` directory

```bash
mkdir -p nl_processing/database/backend
```

### 2. Create `nl_processing/database/backend/__init__.py`

Empty file (ruff enforced convention).

### 3. Create `nl_processing/database/backend/abstract.py`

Implement the ABC matching the architecture spec exactly:

```python
from abc import ABC, abstractmethod


class AbstractBackend(ABC):
    """Abstract interface for database backends.

    The backend operates on primitives (str, int, dict), not Word objects.
    The DatabaseService layer handles conversion between Word model
    instances and backend primitives.
    """

    @abstractmethod
    async def add_word(
        self, table: str, normalized_form: str, word_type: str
    ) -> int | None:
        """Insert word if not exists, return row id. Return None if already exists."""
        ...

    @abstractmethod
    async def get_word(
        self, table: str, normalized_form: str
    ) -> dict | None:
        """Return row dict {id, normalized_form, word_type} or None."""
        ...

    @abstractmethod
    async def add_translation_link(
        self, table: str, source_id: int, target_id: int
    ) -> None:
        """Create a translation link between source and target word IDs."""
        ...

    @abstractmethod
    async def get_user_words(
        self, user_id: str, language: str, **filters: object
    ) -> list[dict]:
        """Return user's word rows with optional filtering.

        Filters may include: word_type, limit, random.
        """
        ...

    @abstractmethod
    async def add_user_word(
        self, user_id: str, word_id: int, language: str
    ) -> None:
        """Associate a word with a user. Idempotent (no error on duplicate)."""
        ...

    @abstractmethod
    async def create_tables(
        self, languages: list[str], pairs: list[tuple[str, str]]
    ) -> None:
        """Create all required tables (IF NOT EXISTS).

        Args:
            languages: List of language codes (e.g., ["nl", "ru"]).
                       Creates words_{lang} table for each.
            pairs: List of (source_lang, target_lang) tuples.
                   Creates translations_{src}_{tgt} table for each.
        Also creates the user_words table.
        """
        ...
```

**Key design decisions from architecture:**
- Backend operates on primitives (`str`, `int`, `dict`), NOT `Word` objects.
- `add_word` returns `int | None` -- the row ID if newly inserted, `None` if already exists.
- `get_word` returns a dict with keys `{id, normalized_form, word_type}` or `None`.
- `get_user_words` accepts `**filters` for flexible filtering (word_type, limit, random).
- `add_user_word` is idempotent -- no error if the user-word association already exists.
- `create_tables` uses `IF NOT EXISTS` semantics (FR27).
- All methods are `async def` (NFR5).

### 4. Verify

- Run `uv run ruff format nl_processing/database/backend/` and `uv run ruff check nl_processing/database/backend/`.
- File under 200 lines.
- Run `make check`.

## Production safety constraints (mandatory)

- No production impact. Only new source files created, no database operations.

## Anti-disaster constraints (mandatory)

- The interface matches the architecture spec exactly -- any deviation would cascade to T5 and T6.
- Uses Python stdlib only (`abc`), no external dependencies.

## Error handling + correctness rules (mandatory)

- Abstract methods define the contract; error handling is the implementer's responsibility.
- The docstrings specify expected behavior (return `None` for not-found, idempotent for duplicates).

## Zero legacy tolerance rule (mandatory)

- No legacy code affected. These are new files.

## Acceptance criteria (testable)

1. `nl_processing/database/backend/__init__.py` exists (empty)
2. `nl_processing/database/backend/abstract.py` exists with `AbstractBackend` class
3. `AbstractBackend` has all 6 abstract methods: `add_word`, `get_word`, `add_translation_link`, `get_user_words`, `add_user_word`, `create_tables`
4. All methods are `async def` and decorated with `@abstractmethod`
5. `AbstractBackend` cannot be instantiated directly (raises `TypeError`)
6. File under 200 lines
7. `make check` passes 100% green

## Verification / quality gates

- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] Import works: `from nl_processing.database.backend.abstract import AbstractBackend`
- [ ] Instantiation raises `TypeError`: `AbstractBackend()` fails
- [ ] `make check` passes 100% green

## Edge cases

- `get_user_words` `**filters` parameter -- the ABC doesn't validate filters, that's the implementation's job.
- `create_tables` with empty `languages` or `pairs` lists -- implementation should handle gracefully (create only the user_words table).

## Notes / risks

- **Decision made autonomously**: Using `**filters: object` type annotation for the `get_user_words` keyword arguments. This keeps the ABC generic while allowing concrete implementations to accept specific filter parameters.
- The architecture shows `**filters` as the mechanism for `word_type`, `limit`, `random` -- T5 (NeonBackend) will implement the actual SQL filtering.
