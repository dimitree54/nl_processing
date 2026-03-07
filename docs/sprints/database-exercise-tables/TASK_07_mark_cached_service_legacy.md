---
Task ID: `T7`
Title: `Mark cached_service.py as legacy`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T1`
Parallelizable: `yes, with T2–T6`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Mark `cached_service.py` as legacy in accordance with the architecture direction: "legacy prototype helper; superseded by planned database_cache module". Add clear deprecation markers in the module docstring and class docstring. Do not delete the file — it remains functional for backward compatibility until the `database_cache` module is implemented.

## Context (contract mapping)

- Requirements: Sprint request item 4 — "CachedDatabaseService Deprecation"
- Architecture: `cached_service.py # legacy prototype helper; superseded by planned database_cache module`
- Current: `cached_service.py` (74 lines) has a clean docstring with no deprecation notice.

## Preconditions

- T1 completed (pre-existing bug fixed).

## Non-goals

- Deleting the file.
- Changing any behavior or logic.
- Updating tests for `CachedDatabaseService` (they should continue to pass as-is).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database/cached_service.py` — docstrings only

**FORBIDDEN — this task must NEVER touch:**
- Any other source file
- Any test file
- Any other module

**Test scope:**
- Run existing tests to confirm nothing broke: `uv run pytest tests/unit/database/test_service.py -x -v` (CachedDatabaseService tests are here).

## Touched surface (expected files / modules)

- `nl_processing/database/cached_service.py` — docstrings only

## Dependencies and sequencing notes

- Depends only on T1 (must be green).
- Can run in parallel with T2–T6 (no shared files).
- T9 depends on this (for completeness, though no test changes needed).

## Implementation steps (developer-facing)

1. Update the module-level docstring in `cached_service.py`:
   ```python
   """CachedDatabaseService — LEGACY prototype helper.

   .. deprecated::
       Superseded by the planned ``database_cache`` module.
       Retained for backward compatibility. Do not extend.
   """
   ```

2. Update the `CachedDatabaseService` class docstring:
   ```python
   class CachedDatabaseService:
       """LEGACY: Wraps DatabaseService with an in-memory LRU cache for get_words.

       .. deprecated::
           Superseded by the planned ``database_cache`` module.
           Do not add new features to this class.
       """
   ```

3. Run linter:
   ```
   uv run ruff format nl_processing/database/cached_service.py
   uv run ruff check nl_processing/database/cached_service.py
   ```

4. Run existing tests to confirm no regressions:
   ```
   uv run pytest tests/unit/database/test_service.py -x -v -k "cached"
   ```

## Production safety constraints (mandatory)

- **Database operations**: None. Docstring-only change.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: No new code.
- **No regressions**: Only docstrings changed. Behavior unchanged.

## Error handling + correctness rules (mandatory)

- N/A — no logic changes.

## Zero legacy tolerance rule (mandatory)

- This task *marks* legacy. The file is explicitly labeled as deprecated with clear direction (superseded by `database_cache`).

## Acceptance criteria (testable)

1. Module docstring includes "LEGACY" and "deprecated" notice mentioning `database_cache`.
2. Class docstring includes "LEGACY" and "deprecated" notice.
3. No behavioral changes — all existing `CachedDatabaseService` tests pass.
4. `uv run ruff check nl_processing/database/cached_service.py` — no errors.
5. File is ≤ 200 lines (currently 74, change adds ~4 lines).

## Verification / quality gates

- [ ] Linters/formatters pass
- [ ] Existing tests pass unchanged

## Edge cases

- None.

## Notes / risks

- No risks. Docstring-only change.
