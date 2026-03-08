---
Task ID: T3
Title: Create `models.py` module with `CacheStatus`
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T1
Parallelizable: yes, with T2, T4
Owner: Developer
Status: planned
---

## Goal / value

Create the `database_cache` models module defining `CacheStatus` — the status dataclass returned by `init()` and `get_status()`. This model is used by the service layer and consumed by callers.

## Context (contract mapping)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` — FR4 (`init()` returns `CacheStatus`), FR30 (`get_status()` returns readiness, staleness, pending event count, timestamps)
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Module Internal Structure" lists `models.py` for `CacheStatus and internal sync records`
- PRD status shape:
  ```python
  CacheStatus(
      is_ready=True,
      is_stale=False,
      has_snapshot=True,
      pending_events=3,
      last_refresh_completed_at=...,
  )
  ```

## Preconditions

- T1 complete (dependency installed)

## Non-goals

- Defining SQLite table schemas (that's in `local_store.py`, T5)
- Writing tests for models (covered in T9)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database_cache/models.py` — create this file

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- Any existing files

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes

## Touched surface (expected files / modules)

- `nl_processing/database_cache/models.py` (new file)

## Dependencies and sequencing notes

- Depends on T1 only for sequencing
- Can run in parallel with T2 (exceptions) and T4 (logging) — no shared files
- Must complete before T5 (local_store), which uses `CacheStatus`

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pydantic` (already in project dependencies, `>=2.0,<3`)
- **Relevant docs**: https://docs.pydantic.dev/latest/concepts/models/
- **Usage**: `CacheStatus` will be a Pydantic `BaseModel` — consistent with `database.models.ScoredWordPair`, `database.models.WordPair`, and all other models in the project.
- **Known gotchas**: Pydantic v2 uses `model_config` instead of inner `Config` class. `datetime | None` requires no special handling in Pydantic v2.

## Implementation steps (developer-facing)

1. Create `nl_processing/database_cache/models.py`.
2. Define `CacheStatus` as a Pydantic `BaseModel` with the following fields:
   ```python
   from datetime import datetime
   from pydantic import BaseModel

   class CacheStatus(BaseModel):
       is_ready: bool
       is_stale: bool
       has_snapshot: bool
       pending_events: int
       last_refresh_completed_at: datetime | None
       last_flush_completed_at: datetime | None
   ```
3. Fields map to PRD requirements:
   - `is_ready` — FR4, FR7, FR13: True if a usable snapshot exists
   - `is_stale` — FR6: True if snapshot is older than TTL
   - `has_snapshot` — FR5: True if any snapshot exists (even if stale)
   - `pending_events` — FR30: Count of unflushed outbox events
   - `last_refresh_completed_at` — FR30: Timestamp of last successful refresh
   - `last_flush_completed_at` — FR30: Timestamp of last successful flush
4. Run `make check` to verify linter compliance.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses Pydantic `BaseModel`, consistent with existing project models.
- **Correct libraries only**: Pydantic `>=2.0,<3` already in `pyproject.toml`.
- **Correct file locations**: `nl_processing/database_cache/models.py` per architecture spec.
- **No regressions**: New file, no existing code affected.

## Error handling + correctness rules (mandatory)

- N/A — this is a data model definition, no error handling logic.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove — new file.

## Acceptance criteria (testable)

1. File `nl_processing/database_cache/models.py` exists.
2. `CacheStatus` is a Pydantic `BaseModel` with fields: `is_ready`, `is_stale`, `has_snapshot`, `pending_events`, `last_refresh_completed_at`, `last_flush_completed_at`.
3. `last_refresh_completed_at` and `last_flush_completed_at` are `datetime | None`.
4. `pending_events` is `int`.
5. `is_ready`, `is_stale`, `has_snapshot` are `bool`.
6. File is ≤ 200 lines.
7. `make check` passes.

## Verification / quality gates

- [ ] File exists with correct content
- [ ] `make check` passes
- [ ] No new warnings introduced

## Edge cases

- None for this task.

## Notes / risks

- `CacheStatus` may gain additional fields during implementation (e.g., `last_error`). The PRD mentions "last background error" in FR31/FR32 but the planned shape in the PRD doesn't include it. The developer should add it if needed during T7 (service implementation), keeping this model as the canonical status contract.
