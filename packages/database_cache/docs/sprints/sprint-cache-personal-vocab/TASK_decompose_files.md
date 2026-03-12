---
Task ID: `T1`
Title: `Decompose service.py and local_store.py to stay under 200-line limit`
Sprint: `2026-03-12_cache-personal-vocab`
Module: `database_cache`
Depends on: —
Parallelizable: no
---

## Goal / value

Extract helper functions and base infrastructure from `service.py` (190 lines) and `local_store.py` (196 lines) into dedicated files so that subsequent tasks can add new methods without exceeding the 200-line pylint limit. After this task, both files should be at ~150–160 lines, providing ~40+ lines of headroom.

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — no functional requirements changed; this is a structural prerequisite
- Module spec: `docs/module-spec.md`
- AGENTS.md file-size rule: files above 180 lines are a weak signal for refactoring; 200 is the hard limit

## Preconditions

- Current `service.py` is 190 lines
- Current `local_store.py` is 196 lines
- All existing tests pass before starting

## Non-goals

- Adding any new public API methods (those come in T2–T5)
- Changing any behavior or public interfaces
- Modifying test files (unless imports change due to moved functions)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `src/nl_processing/database_cache/` — module source code
- `tests/unit/database_cache/` — unit tests (only if imports need updating)
- `tests/integration/database_cache/` — integration tests (only if imports need updating)
- `tests/e2e/database_cache/` — E2E tests (only if imports need updating)

**FORBIDDEN — this task must NEVER touch:**
- `src/nl_processing/core/` or any `core` package file
- `src/nl_processing/database/` or any `database` package file
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/unit/database_cache/`, `tests/integration/database_cache/`
- Test command: `uv run pytest tests/unit/database_cache/ tests/integration/database_cache/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `src/nl_processing/database_cache/service.py` — shrinks by extracting helpers
- `src/nl_processing/database_cache/_service_helpers.py` — **new file** with extracted helpers
- `src/nl_processing/database_cache/local_store.py` — shrinks by extracting base layer
- `src/nl_processing/database_cache/_local_store_base.py` — **new file** with base class / utility methods

## Dependencies and sequencing notes

- No dependencies — this is the first task
- All subsequent tasks (T2–T6) depend on this decomposition being complete
- Must not change any public behavior — pure refactoring

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries are introduced. This task only reorganizes existing code.

## Implementation steps (developer-facing)

### Step 1: Extract `_service_helpers.py` from `service.py`

1. Create `src/nl_processing/database_cache/_service_helpers.py`.
2. Move the following from `service.py` into it:
   - `_parse_dt(meta, key)` function (lines 186–190)
   - `_row_to_word_pair()` — currently a method on `DatabaseCacheService`. Convert to a module-level function `row_to_word_pair(row, source_language, target_language)` that takes the two `Language` params explicitly instead of reading `self._source_language` / `self._target_language`. Update `service.py` to call the extracted function.
   - `_background_refresh()` and `_background_flush()` — currently private methods (lines 171–183). These are thin wrappers around `self._syncer`. Keep them in `service.py` (they're only 12 lines combined and reference `self`). **Do not extract** — not worth the indirection.
3. Update `service.py` imports to use the extracted functions.
4. Verify `service.py` is now ~155–160 lines.

### Step 2: Extract `_local_store_base.py` from `local_store.py`

1. Create `src/nl_processing/database_cache/_local_store_base.py`.
2. Move the following from `local_store.py` into it:
   - `_now()` module-level function (line 19–20)
   - The `LocalStoreBase` class containing: `__init__`, `_conn` property, `open()`, `close()`, `_fetch_all()`, `_exec_commit()` — these are the generic SQLite infrastructure methods (~55 lines).
3. Change `LocalStore` in `local_store.py` to inherit from `LocalStoreBase`.
4. Remove the moved methods from `local_store.py` and update any internal references.
5. Verify `local_store.py` is now ~150–160 lines.

### Step 3: Verify existing tests still pass

1. Run `uv run pytest tests/unit/database_cache/ -x -v`.
2. Run `uv run pytest tests/integration/database_cache/ -x -v`.
3. If any test imports `_parse_dt` or other moved symbols directly (check: none currently do), update the imports.
4. Verify no new lint warnings.

### Step 4: Line-count verification

1. Confirm `service.py` < 170 lines.
2. Confirm `local_store.py` < 170 lines.
3. Confirm `_service_helpers.py` < 50 lines.
4. Confirm `_local_store_base.py` < 60 lines.

## Production safety constraints (mandatory)

The current application version is **running in production on this same machine** (different directory). Shared local resources must not be disrupted.

- **Database operations**: No database operations in this task. Pure code reorganization.
- **No behavior changes**: All public APIs remain identical. Only internal module structure changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: This task extracts existing code rather than duplicating it.
- **Correct file locations**: New files follow the existing `_` prefix convention for internal modules (`_service_helpers.py`, `_local_store_base.py`).
- **No regressions**: All existing tests must pass unchanged (or with minimal import path updates).

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: Not applicable — no error handling changes.
- No behavior changes at all — pure structural refactoring.

## Zero legacy tolerance rule (mandatory)

After implementing this task:

- The original monolithic methods are removed from their source files (not left as dead code alongside the extracted versions).
- No duplicate function definitions exist.

## Acceptance criteria (testable)

1. `service.py` is under 170 lines and retains all its existing public methods with identical signatures.
2. `local_store.py` is under 170 lines and retains all its existing public methods with identical signatures.
3. `_service_helpers.py` exists and contains the extracted helper functions.
4. `_local_store_base.py` exists and contains the extracted base class.
5. All existing unit tests pass: `uv run pytest tests/unit/database_cache/ -x -v`.
6. All existing integration tests pass: `uv run pytest tests/integration/database_cache/ -x -v`.
7. No new lint warnings introduced.

## Verification / quality gates

- [ ] Unit tests pass: `uv run pytest tests/unit/database_cache/ -x -v`
- [ ] Integration tests pass: `uv run pytest tests/integration/database_cache/ -x -v`
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Line counts verified: `service.py` < 170, `local_store.py` < 170
- [ ] All public APIs unchanged (same signatures, same behavior)

## Edge cases

- Test files that import from `service.py` or `local_store.py` by reaching into private members (e.g., `local_store._conn`) — these should still work because `LocalStore` inherits from `LocalStoreBase` and exposes the same attributes.
- `_now()` is used in `local_store.py` directly — after extraction to `_local_store_base.py`, import must be updated or it must be available via inheritance context.

## Notes / risks

- **Risk**: Over-extraction could make the code harder to follow.
  - **Mitigation**: Only extract what's needed to create headroom. Keep domain-specific methods in their original files. The base class contains only generic SQLite plumbing.
- **Risk**: Test files reference `local_store._conn` directly for low-level assertions.
  - **Mitigation**: Since `LocalStore` inherits from `LocalStoreBase`, `._conn` remains accessible with the same semantics.
