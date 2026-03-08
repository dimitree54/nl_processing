---
Task ID: T13
Title: Update shared docs (`docs/architecture.md`, `docs/prd.md`) to include `database_cache`
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T8
Parallelizable: yes, with T9, T10, T11, T12, T14
Owner: Developer
Status: planned
---

## Goal / value

Update the shared project documentation (`docs/architecture.md` and `docs/prd.md`) to reference the new `database_cache` module. Remove any remaining references to the old `CachedDatabaseService` that was previously removed from the codebase. After this task, shared docs accurately reflect the current module inventory.

## Context (contract mapping)

- Current state of `docs/architecture.md`:
  - Lists 5 modules: `extract_text_from_image`, `extract_words_from_text`, `translate_text`, `translate_word`, `database`
  - Module architecture references section does NOT include `database_cache`
  - Database module description references `CachedDatabaseService` (which no longer exists)
  - Directory structure does not show `database_cache/`
  - Test structure does not show `database_cache/`
- Current state of `docs/prd.md`:
  - Module PRD References table lists 5 modules — no `database_cache`
  - Module dependencies section mentions `database` but not `database_cache`

## Preconditions

- T8 complete (module implemented and importable — needed to verify accuracy of doc updates)

## Non-goals

- Rewriting the shared docs from scratch
- Updating module-specific docs (that's T14)
- Changing module code

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `docs/architecture.md` — update to include `database_cache`
- `docs/prd.md` — update to include `database_cache`

**FORBIDDEN — this task must NEVER touch:**
- Any module source code
- Any test files
- Any module-specific docs

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes

## Touched surface (expected files / modules)

- `docs/architecture.md`
- `docs/prd.md`

## Dependencies and sequencing notes

- Depends on T8 (module exists — needed to accurately describe its structure)
- Can run in parallel with T9–T12 and T14
- Zero risk of merge conflicts with test tasks (different files)

## Third-party / library research (mandatory for any external dependency)

- No third-party libraries involved — documentation only.

## Implementation steps (developer-facing)

### `docs/architecture.md` updates:

1. **Module architecture references** (near the top): Add a reference to `database_cache`:
   ```markdown
   > - [`database_cache`](../../nl_processing/database_cache/docs/architecture_database_cache.md)
   ```

2. **Project directory structure**: Add `database_cache/` to the source package tree:
   ```
   │   ├── database_cache/                   # module 6: local-first SQLite cache
   │   │   ├── __init__.py                   # empty
   │   │   ├── service.py                    # DatabaseCacheService (public class)
   │   │   ├── local_store.py                # SQLite schema + local transactions
   │   │   ├── sync.py                       # refresh / flush orchestration
   │   │   ├── models.py                     # CacheStatus model
   │   │   ├── exceptions.py                 # CacheNotReadyError, CacheStorageError, CacheSyncError
   │   │   ├── logging.py                    # Module logger
   │   │   └── docs/
   │   │       ├── product-brief-database_cache-2026-03-07.md
   │   │       ├── prd_database_cache.md
   │   │       └── architecture_database_cache.md
   ```

3. **Test directory structure**: Add `database_cache/` to all three test levels:
   ```
   │   ├── unit/
   │   │   └── database_cache/              # module 6 unit tests
   │   ├── integration/
   │   │   └── database_cache/              # module 6 integration tests
   │   └── e2e/
   │       └── database_cache/              # module 6 e2e tests
   ```

4. **Module public interface pattern**: Add `database_cache` import example:
   ```python
   from nl_processing.database_cache.service import DatabaseCacheService
   ```

5. **Architectural boundaries**: Update the module dependency note:
   - `database_cache` depends on `database` (`ExerciseProgressStore`) — intentional downstream consumer.
   - `sampling` should prefer `database_cache` as its hot-path source (future sprint).

6. **Data flow**: Add `database_cache` to the data flow diagram:
   ```
   [database] ←→ [database_cache] ← [sampling]
   ```

7. **Remove CachedDatabaseService references**: Search for any mentions of `CachedDatabaseService` and remove or replace them. The `database` module's `__init__.py` description currently says `# public exports: DatabaseService, CachedDatabaseService` — update to just `DatabaseService`. The `service.py` description says `# DatabaseService, CachedDatabaseService (public classes)` — update to just `DatabaseService`.

### `docs/prd.md` updates:

1. **Module PRD References table**: Add a row for `database_cache`:
   ```markdown
   | `database_cache` | `nl_processing/database_cache/docs/prd_database_cache.md` |
   ```

2. **Module dependencies section**: Add a note that `database_cache` depends on `database` (similar to the existing note about `database` depending on `translate_word`).

3. **Dependencies section (SNFR8)**: Add `aiosqlite` as a module-specific dependency for `database_cache`.

## Production safety constraints (mandatory)

- **Database operations**: N/A — documentation only.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow existing doc patterns (look at how `database` module is referenced).
- **Correct file locations**: Only modifying existing docs in `docs/`.
- **No regressions**: Documentation changes don't affect runtime behavior.

## Error handling + correctness rules (mandatory)

- N/A — documentation changes.

## Zero legacy tolerance rule (mandatory)

- **CRITICAL**: Remove all references to `CachedDatabaseService` from shared docs. This class no longer exists and must not be referenced anywhere.
- Verify no stale module counts (update "6 packages" if the old text says "5 modules" or similar).

## Acceptance criteria (testable)

1. `docs/architecture.md` references `database_cache` in the module list, directory structure, test structure, and data flow.
2. `docs/architecture.md` contains no references to `CachedDatabaseService`.
3. `docs/prd.md` Module PRD References table includes `database_cache`.
4. `docs/prd.md` Module dependencies section mentions `database_cache`.
5. `make check` passes.

## Verification / quality gates

- [ ] `CachedDatabaseService` grep returns 0 matches in `docs/architecture.md`
- [ ] `CachedDatabaseService` grep returns 0 matches in `docs/prd.md`
- [ ] `database_cache` appears in both shared doc files
- [ ] `make check` passes

## Edge cases

- None for this task.

## Notes / risks

- **Risk**: Other parts of shared docs may reference the old caching approach. Grep for `CachedDatabase`, `cached_database`, and `cache` to find all mentions.
  - **Mitigation**: Do a thorough search before considering this task complete.
