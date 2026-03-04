---
Task ID: `T2`
Title: `Add asyncpg dependency and configure Neon dev database in Doppler`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The `asyncpg` library is available as a project dependency, a Neon dev database exists, and `DATABASE_URL` is configured in the Doppler `dev` environment. This enables all subsequent tasks to connect to a real PostgreSQL database for integration and e2e testing.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- NFR15 (asyncpg dependency), FR16 (DATABASE_URL)
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Neon PostgreSQL as First Backend", "Doppler Environment Strategy for Testing"
- Shared architecture: `docs/planning-artifacts/architecture.md` -- dependency management via `pyproject.toml`

## Preconditions

- T1 completed: `make check` is green.

## Non-goals

- Writing any module code (that's T3+)
- Creating database tables (that's T6)
- Configuring `stg` or `prd` Doppler environments (those already exist for production)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `pyproject.toml` -- add `asyncpg` to `[project] dependencies`

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/` -- no module code yet
- `tests/` -- no test code yet
- `Makefile`, `ruff.toml`, `pytest.ini` -- project config
- Any Doppler `prd` or `stg` environments

**Test scope:**
- No new tests in this task.
- Verification: `make check` still passes after adding the dependency.

## Touched surface (expected files / modules)

- `pyproject.toml` -- add `asyncpg` dependency
- Doppler `dev` environment -- add `DATABASE_URL` secret (manual/CLI)
- Neon console/CLI -- create dev database (manual/CLI)

## Dependencies and sequencing notes

- Depends on T1 for green baseline.
- All subsequent tasks depend on `asyncpg` being available.
- T5+ depend on `DATABASE_URL` being configured in Doppler `dev`.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncpg` v0.31.0 (latest stable, released Nov 24, 2025)
- **Official documentation**: https://magicstack.github.io/asyncpg/current/
- **API reference**: https://magicstack.github.io/asyncpg/current/api/index.html
- **PyPI**: https://pypi.org/project/asyncpg/
- **Key APIs used in this project**:
  - `asyncpg.connect(dsn)` -- single connection: https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.connect
  - `asyncpg.create_pool(dsn)` -- connection pool: https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.pool.create_pool
  - `pool.acquire()` -- borrow connection from pool
  - `conn.execute(query, *args)` -- execute without return
  - `conn.fetch(query, *args)` -- fetch multiple rows as `list[Record]`
  - `conn.fetchrow(query, *args)` -- fetch single row as `Record | None`
  - `conn.fetchval(query, *args)` -- fetch single value
- **Connection string format**: Standard PostgreSQL DSN: `postgresql://user:password@host:port/database?sslmode=require`
- **Neon-specific**: Neon uses standard PostgreSQL protocol. `asyncpg` connects to Neon identically to any PostgreSQL server. SSL is required (`sslmode=require` in DSN).
- **Known gotchas**:
  - `asyncpg` uses `$1, $2` parameter placeholders (not `%s` like psycopg)
  - Connection pool should be created once and reused, not per-request
  - Neon cold starts may add ~100-300ms to the first connection
- **Version constraint**: `>=0.30,<1` -- allows patch updates, excludes future major version

## Implementation steps (developer-facing)

1. **Add `asyncpg` to `pyproject.toml`**:

   In `[project] dependencies`, add:
   ```
   "asyncpg>=0.30,<1",
   ```

   The full dependencies list becomes:
   ```toml
   dependencies = [
     "pydantic>=2.0,<3",
     "langchain>=0.3,<1",
     "langchain-openai>=0.3,<1",
     "opencv-python>=4.10,<5",
     "asyncpg>=0.30,<1",
   ]
   ```

2. **Run `uv sync`** to install the new dependency and update the lockfile.

3. **Create a Neon dev database** (if not already exists):
   - Go to https://console.neon.tech/ or use the Neon CLI
   - Create a new database named `nl_processing_dev` (or similar) in the existing Neon project
   - Note the connection string (DSN)

4. **Configure Doppler `dev` environment**:
   - Add `DATABASE_URL` secret with the Neon dev database connection string
   - Verify: `doppler run --config dev -- printenv DATABASE_URL` shows the connection string
   - **CRITICAL**: Do NOT modify the `prd` or `stg` Doppler environments

5. **Verify connectivity** (quick manual check):
   ```bash
   doppler run -- python -c "
   import asyncio, asyncpg, os
   async def check():
       conn = await asyncpg.connect(os.environ['DATABASE_URL'])
       result = await conn.fetchval('SELECT 1')
       print(f'Connected OK, SELECT 1 = {result}')
       await conn.close()
   asyncio.run(check())
   "
   ```

6. **Run `make check`** to verify no regressions from the new dependency.

## Production safety constraints (mandatory)

- **Database operations**: The only DB operation in this task is a manual `SELECT 1` connectivity test against the dev database. No tables are created.
- **Resource isolation**: Doppler `dev` environment is completely separate from `prd`. The `DATABASE_URL` in `dev` points to `nl_processing_dev`, not the production database.
- **CRITICAL**: Never add or modify `DATABASE_URL` in the `prd` Doppler environment during this sprint.

## Anti-disaster constraints (mandatory)

- `asyncpg` version is pinned to `>=0.30,<1` -- avoids surprise major version bumps.
- The dependency is already listed in the architecture doc as a module-specific dependency (NFR15).
- No new top-level directories or files created.

## Error handling + correctness rules (mandatory)

- If `DATABASE_URL` is not set in Doppler `dev`, the connectivity test fails immediately. This is expected behavior -- the env var must be configured.
- No error silencing.

## Zero legacy tolerance rule (mandatory)

- No legacy code affected in this task.

## Acceptance criteria (testable)

1. `asyncpg` appears in `pyproject.toml` `[project] dependencies`
2. `uv sync` succeeds and `asyncpg` is importable: `uv run python -c "import asyncpg; print(asyncpg.__version__)"`
3. `DATABASE_URL` is configured in Doppler `dev` environment
4. `doppler run -- python -c "import asyncio, asyncpg, os; ..."` connectivity test succeeds with `SELECT 1 = 1`
5. `make check` passes 100% green (no regressions from new dependency)

## Verification / quality gates

- [ ] `asyncpg` importable: `uv run python -c "import asyncpg"`
- [ ] Doppler dev has DATABASE_URL: `doppler run --config dev -- printenv DATABASE_URL`
- [ ] Connectivity test passes
- [ ] `make check` passes 100% green

## Edge cases

- Neon may require `sslmode=require` in the connection string. Most Neon-provided connection strings include this by default.
- If the Neon free tier has connection limits, ensure the dev database is not shared with other services.

## Notes / risks

- **Decision made autonomously**: Using `>=0.30,<1` version range for `asyncpg`. The latest version is 0.31.0 (Nov 2025). Pinning to `>=0.30` ensures compatibility with Neon PostgreSQL.
- **Risk**: Neon cold start latency may affect first connections. This is expected and handled in T5 (connection pooling) and T10 (latency benchmarks).
