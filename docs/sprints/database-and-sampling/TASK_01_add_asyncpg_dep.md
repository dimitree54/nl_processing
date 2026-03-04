---
Task ID: `T1`
Title: `Add asyncpg dependency to pyproject.toml`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `—`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

`asyncpg` is available as a project dependency so that all subsequent database module tasks can import it. The dependency is pinned to a stable version range consistent with project conventions.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — NFR15: asyncpg is a required dependency
- Architecture: `nl_processing/database/docs/architecture_database.md` — Decision: Neon PostgreSQL as First Backend (asyncpg)
- Shared architecture: `docs/planning-artifacts/architecture.md` — asyncpg listed under Technical Constraints & Dependencies

## Preconditions

- `pyproject.toml` exists and is the project's dependency manifest
- `uv` package manager is available

## Non-goals

- No code files created or modified (only dependency manifest)
- No database connections tested yet

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `pyproject.toml` — add asyncpg to dependencies

**FORBIDDEN — this task must NEVER touch:**

- Any module source code
- Any test files
- Makefile, ruff.toml, pytest.ini

**Test scope:**

- Test command: `make check` — must still pass with all existing 26 tests
- No new tests in this task

## Touched surface (expected files / modules)

- `pyproject.toml`

## Dependencies and sequencing notes

- No dependencies — this is the first task
- All subsequent tasks depend on this

## Third-party / library research (mandatory for any external dependency)

- **Library/API**: asyncpg 0.31.0 (latest stable as of 2025-11-24)
- **Official documentation**: https://magicstack.github.io/asyncpg/current/
- **API reference**: https://magicstack.github.io/asyncpg/current/api/index.html
- **PyPI page**: https://pypi.org/project/asyncpg/
- **Usage examples (verified current)**:
  ```python
  import asyncpg
  conn = await asyncpg.connect(dsn="postgresql://user:pass@host/db")
  row = await conn.fetchrow("SELECT 1 AS val")
  await conn.close()
  ```
- **Known gotchas / breaking changes**: asyncpg 0.30.0 dropped Python 3.8 support. 0.31.0 is stable for Python 3.9-3.14. No known issues with Neon PostgreSQL — Neon officially supports asyncpg.
- **Version pin rationale**: `>=0.30,<1` — matches project convention (major version pinning). 0.30+ ensures modern Python compatibility. asyncpg follows semver so <1 is safe.

## Implementation steps (developer-facing)

1. Open `pyproject.toml`.
2. Add `"asyncpg>=0.30,<1"` to the `dependencies` list under `[project]`.
3. Run `uv sync --all-groups` to install the new dependency and update `uv.lock`.
4. Run `make check` to verify all existing 26 tests still pass.

## Production safety constraints (mandatory)

- **Database operations**: None — this task only adds a dependency.
- **Resource isolation**: No runtime resources used.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using the community-standard asyncpg library as specified in architecture.
- **Correct libraries only**: asyncpg is explicitly specified in architecture doc under "Module-Specific Dependencies" (NFR15).
- **Correct file locations**: Only modifying `pyproject.toml` at project root — standard location.
- **No regressions**: Dependency addition only; no code changes.

## Error handling + correctness rules (mandatory)

- N/A — no code in this task.

## Zero legacy tolerance rule (mandatory)

- N/A — no code changes.

## Acceptance criteria (testable)

1. `pyproject.toml` contains `asyncpg` in the `dependencies` list with version constraint `>=0.30,<1`.
2. `uv sync --all-groups` succeeds without errors.
3. `python -c "import asyncpg; print(asyncpg.__version__)"` runs successfully under `uv run`.
4. `make check` passes with all 26 existing tests.

## Verification / quality gates

- [ ] `uv sync --all-groups` succeeds
- [ ] `uv run python -c "import asyncpg"` succeeds
- [ ] `make check` passes (26 tests, all linters green)

## Edge cases

- If asyncpg has C extension build issues on macOS, ensure Xcode Command Line Tools are installed. asyncpg 0.31.0 provides pre-built wheels for macOS ARM64 and x86_64.

## Notes / risks

- **Risk**: asyncpg install requires a C compiler if no wheel is available.
  - **Mitigation**: Pre-built wheels exist for macOS ARM64/x86_64 and all major Linux platforms for Python 3.12+. Extremely unlikely to need compilation.
