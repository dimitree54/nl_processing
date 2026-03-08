---
Task ID: T2
Title: Create `exceptions.py` module
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T1
Parallelizable: yes, with T3, T4
Owner: Developer
Status: planned
---

## Goal / value

Create the `database_cache` exceptions module defining `CacheNotReadyError`, `CacheStorageError`, and `CacheSyncError`. These are used by all other module files to raise domain-specific errors.

## Context (contract mapping)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` — "Exceptions" section: `CacheNotReadyError`, `CacheStorageError`, `CacheSyncError`
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Module Internal Structure" lists `exceptions.py`
- Pattern reference: `nl_processing/database/exceptions.py` — existing exception module pattern (simple classes, docstrings, no logic)

## Preconditions

- T1 complete (dependency installed, though not strictly needed for this file)

## Non-goals

- Writing tests for exceptions (covered in T9)
- Implementing any exception-handling logic (that's in service/sync/local_store)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database_cache/exceptions.py` — create this file

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- Any existing files

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes

## Touched surface (expected files / modules)

- `nl_processing/database_cache/exceptions.py` (new file)

## Dependencies and sequencing notes

- Depends on T1 only for sequencing (no actual code dependency on `aiosqlite`)
- Can run in parallel with T3 (models) and T4 (logging) — they don't share files
- Must complete before T5 (local_store), which imports these exceptions

## Third-party / library research (mandatory for any external dependency)

- No third-party libraries needed — pure Python exception classes.

## Implementation steps (developer-facing)

1. Create `nl_processing/database_cache/exceptions.py`.
2. Define three exception classes, each with a docstring:
   ```python
   class CacheNotReadyError(Exception):
       """Raised when cached data is requested before the first usable snapshot exists."""

   class CacheStorageError(Exception):
       """Raised when the local SQLite cache file cannot be opened, read, or updated."""

   class CacheSyncError(Exception):
       """Raised when an explicit refresh or flush operation fails synchronously."""
   ```
3. No base class other than `Exception` is needed (follows the pattern in `nl_processing/database/exceptions.py`).
4. Run `make check` to verify the file passes all linters.

## Production safety constraints (mandatory)

- **Database operations**: N/A — no database work.
- **Resource isolation**: N/A — only creating a new source file.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the existing exception pattern from `nl_processing/database/exceptions.py`.
- **Correct libraries only**: No external libraries — stdlib `Exception` only.
- **Correct file locations**: `nl_processing/database_cache/exceptions.py` per architecture spec.
- **No regressions**: New file, no existing code affected.

## Error handling + correctness rules (mandatory)

- Each exception class must have a clear docstring explaining when it is raised.
- No empty `__init__` overrides — inherit `Exception.__init__` unchanged.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove — this is a new file.

## Acceptance criteria (testable)

1. File `nl_processing/database_cache/exceptions.py` exists.
2. File defines exactly three classes: `CacheNotReadyError`, `CacheStorageError`, `CacheSyncError`.
3. All three inherit from `Exception`.
4. Each class has a docstring.
5. File is ≤ 200 lines.
6. `make check` passes.

## Verification / quality gates

- [ ] File exists with correct content
- [ ] `make check` passes (ruff format, ruff check, pylint, vulture)
- [ ] No new warnings introduced

## Edge cases

- None for this task.

## Notes / risks

- Minimal risk — 3 simple exception classes following an established pattern.
