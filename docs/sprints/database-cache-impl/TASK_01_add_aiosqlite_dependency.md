---
Task ID: T1
Title: Add `aiosqlite` dependency to `pyproject.toml`
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: —
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Add the `aiosqlite` library as a project dependency so that all subsequent tasks can use it for async SQLite access.

## Context (contract mapping)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` — NFR10 ("no external cache server; local persistence uses embedded local database")
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Local Durable Store Is SQLite" decision
- Shared architecture: `docs/architecture.md` — dependency management via `pyproject.toml` (SNFR9)

## Preconditions

- `pyproject.toml` exists and is valid

## Non-goals

- Writing any module source code
- Writing any tests

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `pyproject.toml` — to add `aiosqlite` dependency line

**FORBIDDEN — this task must NEVER touch:**
- Any source code files
- Any test files
- Any other config files

**Test scope:**
- No tests to write for this task
- Verification: `uv sync` succeeds and `uv run python -c "import aiosqlite"` succeeds

## Touched surface (expected files / modules)

- `pyproject.toml`

## Dependencies and sequencing notes

- No prior tasks needed
- All subsequent tasks (T2–T14) depend on this completing first because `aiosqlite` must be installable

## Third-party / library research (mandatory for any external dependency)

- **Library**: `aiosqlite` — latest stable version: `0.21.0` (as of March 2026)
- **Official documentation**: https://aiosqlite.omnilib.dev/en/stable/
- **PyPI page**: https://pypi.org/project/aiosqlite/
- **API reference**: https://aiosqlite.omnilib.dev/en/stable/api.html
- **Usage examples (verified current)**:
  ```python
  import aiosqlite

  async with aiosqlite.connect("cache.db") as db:
      await db.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY)")
      await db.execute("INSERT INTO t (id) VALUES (?)", (1,))
      await db.commit()
      async with db.execute("SELECT * FROM t") as cursor:
          rows = await cursor.fetchall()
  ```
- **Known gotchas / breaking changes**:
  - `aiosqlite` wraps the stdlib `sqlite3` module; it runs SQLite operations in a dedicated background thread.
  - Row factory must be set explicitly (`db.row_factory = aiosqlite.Row`) for dict-like access.
  - `aiosqlite` 0.20+ requires Python >=3.8; 0.21 supports Python 3.12+.
  - All operations must be awaited; forgetting `await` on `commit()` is a common mistake.

## Implementation steps (developer-facing)

1. Open `pyproject.toml`.
2. In the `[project] dependencies` list, add `"aiosqlite>=0.20,<1"` after the existing `asyncpg` line.
3. Run `uv sync` to install the new dependency and update `uv.lock`.
4. Verify installation: `uv run python -c "import aiosqlite; print(aiosqlite.__version__)"`.

## Production safety constraints (mandatory)

- **Database operations**: N/A — no database work in this task.
- **Resource isolation**: N/A — only modifying a dependency manifest.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: `aiosqlite` is a well-established library; no custom SQLite wrapper needed.
- **Correct libraries only**: Version range `>=0.20,<1` follows the same pattern as existing deps in `pyproject.toml` (e.g., `asyncpg>=0.30,<1`).
- **Correct file locations**: Dependency added to existing `pyproject.toml`, not a new file.
- **No regressions**: Adding a dependency does not affect existing code.

## Error handling + correctness rules (mandatory)

- N/A — this task only adds a dependency line.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove — this is a new addition.

## Acceptance criteria (testable)

1. `pyproject.toml` contains `"aiosqlite>=0.20,<1"` in the `dependencies` list.
2. `uv sync` completes without errors.
3. `uv run python -c "import aiosqlite"` exits with code 0.
4. `make check` passes (existing tests still pass with new dependency present).

## Verification / quality gates

- [ ] `uv sync` succeeds
- [ ] `uv run python -c "import aiosqlite"` succeeds
- [ ] `make check` passes (no regressions)

## Edge cases

- None for this task.

## Notes / risks

- **Risk**: `aiosqlite` version conflict with existing dependencies.
  - **Mitigation**: `aiosqlite` has no dependencies beyond stdlib `sqlite3`; version conflict is extremely unlikely.
