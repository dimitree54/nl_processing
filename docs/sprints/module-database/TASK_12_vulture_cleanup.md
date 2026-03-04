---
Task ID: `T12`
Title: `Update vulture whitelist and run final make check verification`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T6`
Parallelizable: `yes, with T9, T10, T11`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The vulture whitelist is updated to reflect the new module state: the stale `save_translation` reference is removed (since that function no longer exists after T6), and any new public symbols that vulture falsely flags as unused are whitelisted. `make check` passes 100% green with all module code and all three test levels.

## Context (contract mapping)

- Requirements: N/A (code hygiene task)
- Architecture: `docs/planning-artifacts/architecture.md` -- "Tooling Stack" section (vulture for dead code detection)
- Current whitelist: `vulture_whitelist.py` -- currently whitelists `save_translation`

## Preconditions

- T6 completed: `save_translation` is deleted, `DatabaseService` exists.
- Ideally all other tasks (T7-T11) are also completed for a final verification pass.

## Non-goals

- Module code changes (only whitelist file)
- New feature implementation

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `vulture_whitelist.py` -- update entries

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/` -- no module source code
- `tests/` -- no test files
- Any other config files

**Test scope:**
- Verification: `make check` (full quality gate)

## Touched surface (expected files / modules)

- `vulture_whitelist.py` -- update entries

## Dependencies and sequencing notes

- Depends on T6 (which deletes `save_translation`).
- Can run in parallel with T9-T11 (but ideally run last for final verification).
- This is a cleanup task -- no functional dependencies.

## Third-party / library research (mandatory for any external dependency)

- **Tool**: `vulture` v2.14.x (already in dev dependencies)
  - Scans Python files for unused code (functions, imports, variables)
  - Whitelist file: `vulture_whitelist.py` -- list false positives
  - Run: `uv run vulture nl_processing tests vulture_whitelist.py`
  - Docs: https://github.com/jendrikseipp/vulture

## Implementation steps (developer-facing)

### 1. Remove stale `save_translation` whitelist entry

The current `vulture_whitelist.py` contains:

```python
from nl_processing.database.service import save_translation
```

This import will fail after T6 (the function no longer exists). Remove this line.

### 2. Run vulture to check for new false positives

```bash
uv run vulture nl_processing tests vulture_whitelist.py
```

Check if any new database module symbols are flagged as unused. Common candidates:
- `DatabaseService` (if not yet imported by tests at this point)
- `CachedDatabaseService` (if not yet used)
- `ConfigurationError`, `DatabaseError` (if only raised, not imported in tests)
- Test utility functions in `testing.py` (if imported only by test files)

### 3. Add necessary whitelist entries

For any false positives from the database module, add entries:

```python
from nl_processing.database.service import DatabaseService
from nl_processing.database.service import CachedDatabaseService
from nl_processing.database.exceptions import ConfigurationError
from nl_processing.database.exceptions import DatabaseError
from nl_processing.database.models import AddWordsResult
from nl_processing.database.models import WordPair
from nl_processing.database.testing import drop_all_tables
from nl_processing.database.testing import reset_database
from nl_processing.database.testing import count_words
from nl_processing.database.testing import count_user_words
from nl_processing.database.testing import count_translation_links
```

Only add entries that vulture actually reports as unused. Do NOT preemptively whitelist everything.

### 4. Update `__all__` if needed

The whitelist uses `__all__` to export whitelisted names. Add new entries to `__all__`:

```python
__all__ = [
    # ... existing entries ...
    # Add new entries here
]
```

### 5. Run `make check` (full quality gate)

This is the final verification. All of these must pass:
- `uv run ruff format` -- no formatting issues
- `uv run ruff check --fix` -- no lint issues
- `uvx pylint nl_processing tests --disable=all --enable=C0302 --max-module-lines=200` -- all files under 200 lines
- `uvx pylint nl_processing tests --load-plugins=pylint.extensions.bad_builtin --disable=all --enable=W0141 --bad-functions=hasattr,getattr,setattr` -- no bad builtins
- `uv run vulture nl_processing tests vulture_whitelist.py` -- no unused code
- `npx jscpd --exitCode 1` -- no code duplication
- `uv run pytest -n auto tests/unit` -- all unit tests pass
- `doppler run -- uv run pytest -n auto tests/integration` -- all integration tests pass
- `doppler run -- uv run pytest -n auto tests/e2e` -- all e2e tests pass

### 6. Fix any issues

If `make check` reveals any issues:
- Fix formatting with `uv run ruff format`
- Fix lint issues per ruff suggestions
- Fix vulture false positives by adding to whitelist
- Fix jscpd duplications by extracting shared code
- Fix test failures by debugging

## Production safety constraints (mandatory)

- No production impact. Only the vulture whitelist file is modified.

## Anti-disaster constraints (mandatory)

- Only remove entries that correspond to deleted code (`save_translation`).
- Only add entries for actual false positives (verified by running vulture).
- The whitelist is a safety net, not a way to hide real dead code.

## Error handling + correctness rules (mandatory)

- N/A (whitelist file, not executable code).

## Zero legacy tolerance rule (mandatory)

- The stale `save_translation` whitelist entry is removed (it references deleted code).
- No other stale entries should remain.

## Acceptance criteria (testable)

1. `save_translation` import removed from `vulture_whitelist.py`
2. No new vulture errors: `uv run vulture nl_processing tests vulture_whitelist.py` exits 0
3. All new database module public symbols are properly handled (either used in tests or whitelisted)
4. `make check` passes 100% green (all 9 steps)
5. `vulture_whitelist.py` under 200 lines

## Verification / quality gates

- [ ] `uv run vulture nl_processing tests vulture_whitelist.py` exits 0
- [ ] `make check` passes 100% green
- [ ] No stale whitelist entries (all imports resolve)

## Edge cases

- If the database module tests import all public symbols, no whitelist additions may be needed. Run vulture first to check.
- If `jscpd` flags code duplication between database module files (e.g., similar SQL patterns in `neon.py` and `testing.py`), refactor to extract shared helpers.

## Notes / risks

- **Decision made autonomously**: Running this task last (after T11) ensures a complete final verification. However, the `save_translation` removal can be done as soon as T6 is complete.
- This task is lightweight but critical -- it's the final "green light" for the sprint.
