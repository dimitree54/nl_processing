---
Task ID: T12
Title: Update vulture whitelist for `database_cache` public API
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T8
Parallelizable: yes, with T9, T10, T11, T13, T14
Owner: Developer
Status: planned
---

## Goal / value

Update `vulture_whitelist.py` to whitelist `database_cache` public API symbols that vulture would otherwise flag as unused. This is necessary because vulture does static analysis and cannot detect symbols consumed by downstream code (e.g., `sampling` will use `database_cache` in a future sprint).

## Context (contract mapping)

- Pattern reference: `vulture_whitelist.py` — existing whitelist entries for `database`, `sampling`, and other modules
- Architecture: `docs/architecture.md` — "Dead code detection" via vulture in `make check`

## Preconditions

- T8 complete (all module source files exist and are importable)

## Non-goals

- Removing existing whitelist entries
- Whitelisting test-only symbols (they should be used by tests from T9–T11)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `vulture_whitelist.py` — add new entries

**FORBIDDEN — this task must NEVER touch:**
- Any module source code
- Any test files

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes (vulture no longer flags database_cache symbols)

## Touched surface (expected files / modules)

- `vulture_whitelist.py`

## Dependencies and sequencing notes

- Depends on T8 (module must be importable)
- Can run in parallel with T9–T14
- Should be done early to unblock `make check` for other tasks

## Third-party / library research (mandatory for any external dependency)

- **Vulture**: https://github.com/jendrikseipp/vulture — dead code finder.
  - Whitelist pattern: import the symbol or reference the attribute, vulture treats it as "used".
  - Existing project pattern: import classes, then reference their methods/attributes.

## Implementation steps (developer-facing)

1. Open `vulture_whitelist.py`.

2. Add imports for `database_cache` symbols:
   ```python
   from nl_processing.database_cache.exceptions import CacheNotReadyError, CacheStorageError, CacheSyncError
   from nl_processing.database_cache.logging import get_logger as dc_get_logger
   from nl_processing.database_cache.models import CacheStatus
   from nl_processing.database_cache.service import DatabaseCacheService
   ```
   Note: Use `dc_get_logger` alias to avoid name collision with `database.logging.get_logger` already imported.

3. Add attribute references for `DatabaseCacheService` public methods:
   ```python
   # DatabaseCacheService — public API, used by sampling module (future sprint)
   DatabaseCacheService.init  # type: ignore[misc]
   DatabaseCacheService.get_words  # type: ignore[misc]
   DatabaseCacheService.get_word_pairs_with_scores  # type: ignore[misc]
   DatabaseCacheService.record_exercise_result  # type: ignore[misc]
   DatabaseCacheService.refresh  # type: ignore[misc]
   DatabaseCacheService.flush  # type: ignore[misc]
   DatabaseCacheService.get_status  # type: ignore[misc]
   ```

4. Add attribute references for `CacheStatus` fields:
   ```python
   # CacheStatus fields — used by callers
   CacheStatus.is_ready  # type: ignore[misc]
   CacheStatus.is_stale  # type: ignore[misc]
   CacheStatus.has_snapshot  # type: ignore[misc]
   CacheStatus.pending_events  # type: ignore[misc]
   CacheStatus.last_refresh_completed_at  # type: ignore[misc]
   CacheStatus.last_flush_completed_at  # type: ignore[misc]
   ```

5. Add `database_cache` symbols to the `__all__` list.

6. Run `uv run vulture nl_processing tests vulture_whitelist.py` — verify no `database_cache` symbols are flagged.

7. Run `make check` — full pipeline must pass.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow existing whitelist patterns exactly.
- **Correct file locations**: `vulture_whitelist.py` (existing file).
- **No regressions**: Only adding entries, not removing.

## Error handling + correctness rules (mandatory)

- N/A — whitelist file has no runtime logic.

## Zero legacy tolerance rule (mandatory)

- No legacy entries to remove — only additions.

## Acceptance criteria (testable)

1. `vulture_whitelist.py` includes imports for all `database_cache` public symbols.
2. `vulture_whitelist.py` includes attribute references for `DatabaseCacheService` methods and `CacheStatus` fields.
3. `uv run vulture nl_processing tests vulture_whitelist.py` exits with code 0 (no unreachable code flagged for database_cache).
4. `make check` passes.

## Verification / quality gates

- [ ] `uv run vulture nl_processing tests vulture_whitelist.py` passes
- [ ] `make check` passes
- [ ] No new warnings introduced

## Edge cases

- Some symbols may be consumed by tests (T9–T11) and not need whitelisting — only whitelist symbols that vulture still flags after all tests are written.
- If running this before tests are written (parallel with T9), be conservative and whitelist all public API symbols. Remove unnecessary entries later if desired.

## Notes / risks

- **Risk**: Over-whitelisting masks truly dead code. 
  - **Mitigation**: Only whitelist public API symbols documented in the architecture. Internal/private symbols should be used by the module itself.
