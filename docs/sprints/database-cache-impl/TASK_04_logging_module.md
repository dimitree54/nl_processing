---
Task ID: T4
Title: Create `logging.py` module
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T1
Parallelizable: yes, with T2, T3
Owner: Developer
Status: planned
---

## Goal / value

Create the `database_cache` logging module providing a `get_logger()` helper. All other module files will use this to get a namespaced logger for structured log output.

## Context (contract mapping)

- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Module Internal Structure" lists `logging.py`
- Pattern reference: `nl_processing/database/logging.py` — existing `get_logger()` pattern (5 lines)
- Requirements: FR31, FR32 — background refresh/flush failures must be logged

## Preconditions

- T1 complete

## Non-goals

- Configuring log levels or handlers (that's the caller's responsibility)
- Writing tests for the logger (trivial function, tested transitively)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database_cache/logging.py` — create this file

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- Any existing files

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes

## Touched surface (expected files / modules)

- `nl_processing/database_cache/logging.py` (new file)

## Dependencies and sequencing notes

- Depends on T1 only for sequencing
- Can run in parallel with T2 (exceptions) and T3 (models)
- Must complete before T5 (local_store), which imports the logger

## Third-party / library research (mandatory for any external dependency)

- No third-party libraries — uses stdlib `logging` module only.
- Reference: https://docs.python.org/3.12/library/logging.html

## Implementation steps (developer-facing)

1. Create `nl_processing/database_cache/logging.py`.
2. Implement `get_logger()` following the exact pattern from `nl_processing/database/logging.py`:
   ```python
   import logging

   def get_logger(name: str) -> logging.Logger:
       return logging.getLogger(f"nl_processing.database_cache.{name}")
   ```
3. Run `make check` to verify compliance.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Exact copy of the pattern from `nl_processing/database/logging.py`, only changing the namespace prefix.
- **Correct libraries only**: stdlib `logging` — no external dependency.
- **Correct file locations**: `nl_processing/database_cache/logging.py` per architecture spec.
- **No regressions**: New file, no existing code affected.

## Error handling + correctness rules (mandatory)

- N/A — trivial utility function.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove.

## Acceptance criteria (testable)

1. File `nl_processing/database_cache/logging.py` exists.
2. File defines `get_logger(name: str) -> logging.Logger`.
3. `get_logger("test")` returns a `logging.Logger` with name `nl_processing.database_cache.test`.
4. File is ≤ 200 lines.
5. `make check` passes.

## Verification / quality gates

- [ ] File exists with correct content
- [ ] `make check` passes
- [ ] No new warnings introduced

## Edge cases

- None for this task.

## Notes / risks

- Minimal risk — 5-line module following an established pattern.
