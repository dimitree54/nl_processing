---
Task ID: `T3`
Title: `Create exceptions.py, models.py, and logging.py foundation files`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T2`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The module's foundational types exist: `ConfigurationError` and `DatabaseError` exceptions, `AddWordsResult` and `WordPair` Pydantic models, and a structured logging setup. All subsequent tasks import from these files.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- FR17 (ConfigurationError), FR7 (AddWordsResult), FR11 (WordPair), FR19-FR20 (logging)
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Module Internal Structure" (exceptions.py, models.py, logging.py)
- Core models reference: `nl_processing/core/models.py` -- `Word` model used by `AddWordsResult` and `WordPair`

## Preconditions

- T2 completed: `asyncpg` available, `make check` green.

## Non-goals

- Backend implementation (T4-T5)
- Service implementation (T6)
- Tests (T9-T11)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/exceptions.py` -- create new file
- `nl_processing/database/models.py` -- create new file
- `nl_processing/database/logging.py` -- create new file

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/` -- core package (models/exceptions already defined there)
- `nl_processing/database/service.py` -- not yet (T6)
- `nl_processing/database/backend/` -- not yet (T4-T5)
- Any test files
- Other modules

**Test scope:**
- No tests in this task. Verified via import and `make check`.

## Touched surface (expected files / modules)

- `nl_processing/database/exceptions.py` -- new file
- `nl_processing/database/models.py` -- new file
- `nl_processing/database/logging.py` -- new file

## Dependencies and sequencing notes

- Depends on T2 for green baseline.
- T4+ depend on these foundation files.
- These files are pure Python (no external service calls), so no infrastructure needed.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pydantic` v2.x (already in `pyproject.toml`)
  - `BaseModel` for `AddWordsResult` and `WordPair`
  - Docs: https://docs.pydantic.dev/latest/
- **Library**: Python `logging` module (stdlib)
  - `logging.getLogger(name)` with namespace `nl_processing.database`
  - Docs: https://docs.python.org/3/library/logging.html

## Implementation steps (developer-facing)

### 1. Create `nl_processing/database/exceptions.py`

```python
class ConfigurationError(Exception):
    """Raised when required environment variables are missing or invalid.

    Includes setup instructions in the error message.
    """


class DatabaseError(Exception):
    """Raised when a database operation fails.

    Wraps underlying asyncpg/connection errors with clear messages.
    """
```

- Two exception classes, both inheriting from `Exception`.
- `ConfigurationError` is raised at service instantiation when `DATABASE_URL` is missing (FR17).
- `DatabaseError` is raised when database operations fail (NFR8).
- These are module-specific exceptions, separate from `core.exceptions.APIError`.

### 2. Create `nl_processing/database/models.py`

```python
from pydantic import BaseModel

from nl_processing.core.models import Word


class AddWordsResult(BaseModel):
    """Feedback from add_words(): which words were new vs. already in the corpus."""

    new_words: list[Word]
    existing_words: list[Word]


class WordPair(BaseModel):
    """A source Word paired with its translated Word."""

    source: Word
    target: Word
```

- Both models use `Word` from `core.models` (the canonical data type).
- `AddWordsResult` is returned by `add_words()` (FR7).
- `WordPair` is returned by `get_words()` (FR11).
- These are module-internal models, not added to `core`.

### 3. Create `nl_processing/database/logging.py`

```python
import logging


def get_logger(name: str) -> logging.Logger:
    """Get a namespaced logger for the database module.

    All loggers are under the 'nl_processing.database' namespace.
    This enables easy Sentry attachment via LoggingIntegration
    without code changes in the module.

    Args:
        name: Sub-name for the logger (e.g., 'service', 'neon').
              Results in logger named 'nl_processing.database.{name}'.
    """
    return logging.getLogger(f"nl_processing.database.{name}")
```

- Simple helper that returns a namespaced logger.
- Console handler is already configured by Python's default logging. The `pytest.ini` `--log-cli-level=INFO` ensures test output is visible.
- Sentry integration path: add `sentry_sdk` with `LoggingIntegration` that captures `WARNING+` from `nl_processing.database.*` namespace -- no code changes needed (FR20).

### 4. Verify all files

- Each file is well under 200 lines.
- Run `uv run ruff format nl_processing/database/` and `uv run ruff check nl_processing/database/`.
- Run `make check` to verify no regressions.

## Production safety constraints (mandatory)

- No production impact. Only new source files created, no database operations.
- No resource isolation needed.

## Anti-disaster constraints (mandatory)

- Follows existing project patterns: `core.exceptions` for shared exceptions, module-local for module-specific.
- `Word` model is imported from `core.models`, not redefined.
- No new top-level packages or layouts.

## Error handling + correctness rules (mandatory)

- Exception classes are intentionally simple -- message content is the responsibility of the raiser.
- No error silencing patterns.

## Zero legacy tolerance rule (mandatory)

- No legacy code affected. These are new files.

## Acceptance criteria (testable)

1. `nl_processing/database/exceptions.py` exists with `ConfigurationError` and `DatabaseError`
2. `nl_processing/database/models.py` exists with `AddWordsResult` and `WordPair`
3. `nl_processing/database/logging.py` exists with `get_logger()` function
4. All three files are importable: `from nl_processing.database.exceptions import ConfigurationError, DatabaseError`
5. `AddWordsResult` and `WordPair` are valid Pydantic models (can be instantiated with correct args)
6. All files under 200 lines
7. `make check` passes 100% green

## Verification / quality gates

- [ ] Ruff format and check pass for all new files
- [ ] Pylint 200-line limit passes
- [ ] All imports resolve correctly
- [ ] `make check` passes 100% green

## Edge cases

- `AddWordsResult` with empty lists (both `new_words` and `existing_words` can be `[]`).
- `WordPair` requires both `source` and `target` to be valid `Word` instances.

## Notes / risks

- **Decision made autonomously**: Using a simple `get_logger()` helper rather than a complex logging configuration class. This aligns with the architecture's "console handler as initial backend" decision.
- These files are foundational -- if the model fields need to change, all downstream tasks are affected. The fields match the architecture spec exactly.
