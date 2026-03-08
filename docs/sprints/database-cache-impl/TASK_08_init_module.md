---
Task ID: T8
Title: Create `__init__.py` for `database_cache` package
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T7
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Create the `__init__.py` file for the `database_cache` package, making it a proper Python package. Per project conventions (ruff `strictly-empty-init-modules` rule), this file must be empty.

## Context (contract mapping)

- Architecture: `docs/architecture.md` — "Import discipline: Empty `__init__.py` files (enforced by ruff `strictly-empty-init-modules`)"
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Module Internal Structure" lists `__init__.py`
- Ruff config: `ruff.toml` — `strictly-empty-init-modules = true`

## Preconditions

- T7 complete (all source files exist: `exceptions.py`, `models.py`, `logging.py`, `local_store.py`, `sync.py`, `service.py`)

## Non-goals

- Adding any imports or re-exports to `__init__.py` (strictly empty)
- Writing tests

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database_cache/__init__.py` — create this file

**FORBIDDEN — this task must NEVER touch:**
- Any other files

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes (ruff enforces empty init)

## Touched surface (expected files / modules)

- `nl_processing/database_cache/__init__.py` (new file)

## Dependencies and sequencing notes

- Depends on T7 — all source files should exist before creating the package init
- T9 (unit tests), T12 (vulture), T13 (shared docs), T14 (module docs) depend on this
- After this task, the module is import-ready

## Third-party / library research (mandatory for any external dependency)

- No third-party libraries needed.

## Implementation steps (developer-facing)

1. Create an empty file at `nl_processing/database_cache/__init__.py`.
2. Verify: `uv run python -c "import nl_processing.database_cache"` succeeds.
3. Verify: `uv run python -c "from nl_processing.database_cache.service import DatabaseCacheService"` succeeds.
4. Run `make check` — ruff enforces that `__init__.py` is empty.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follows existing pattern (all other `__init__.py` files are empty).
- **Correct file locations**: `nl_processing/database_cache/__init__.py`.
- **No regressions**: New file.

## Error handling + correctness rules (mandatory)

- N/A — empty file.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove.

## Acceptance criteria (testable)

1. File `nl_processing/database_cache/__init__.py` exists.
2. File is empty (0 bytes or whitespace only).
3. `uv run python -c "import nl_processing.database_cache"` exits with code 0.
4. `uv run python -c "from nl_processing.database_cache.service import DatabaseCacheService"` exits with code 0.
5. `make check` passes (ruff `strictly-empty-init-modules` satisfied).

## Verification / quality gates

- [ ] File exists and is empty
- [ ] Import succeeds
- [ ] `make check` passes

## Edge cases

- None for this task.

## Notes / risks

- Trivial task — zero risk.
