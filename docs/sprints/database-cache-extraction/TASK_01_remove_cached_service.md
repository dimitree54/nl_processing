---
Task ID: `T1`
Title: `Remove CachedDatabaseService entirely`
Sprint: `2026-03-07_database-cache-extraction`
Module: `database`
Depends on: `--`
Parallelizable: `yes, with T2, T4`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Eliminate the legacy `CachedDatabaseService` class from the `database` module. All caching logic belongs in the future `database_cache` module. After this task, there is zero in-memory LRU caching code in `database`, and `make check` is green.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- no FR references `CachedDatabaseService`; it is legacy from a prior sprint.
- Architecture: `nl_processing/database/docs/architecture_database.md` line 126 -- already marked "legacy prototype helper; superseded by planned database_cache module".
- Sprint request: Discrepancy 9 -- "`CachedDatabaseService` is legacy and should be removed."

## Preconditions

- `make check` is green before starting.

## Non-goals

- Updating `architecture_database.md` module structure (that is T5).
- Updating the shared architecture (`docs/planning-artifacts/architecture.md`) -- out of scope.
- Updating `README.md` -- out of scope.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/cached_service.py` -- **delete this file**
- `tests/unit/database/conftest.py` -- remove `cached_service` fixture and import
- `tests/unit/database/test_service.py` -- remove CachedDatabaseService tests and import
- `vulture_whitelist.py` -- remove CachedDatabaseService entries

**FORBIDDEN -- this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/database/service.py`
- `nl_processing/database/exercise_progress.py`
- Integration or e2e tests
- `docs/planning-artifacts/`

**Test scope:**
- Verification command: `make check`
- Unit tests affected: `tests/unit/database/test_service.py`, `tests/unit/database/conftest.py`

## Touched surface (expected files / modules)

- `nl_processing/database/cached_service.py` -- delete
- `tests/unit/database/conftest.py` -- remove fixture + import
- `tests/unit/database/test_service.py` -- remove 3 test functions + import
- `vulture_whitelist.py` -- remove 6 lines (import, 3 method refs, comment, `__all__` entry)

## Dependencies and sequencing notes

- No dependencies. This is a self-contained deletion.
- Can run in parallel with T2 and T4 (no file overlap).

## Third-party / library research (mandatory for any external dependency)

N/A -- no new libraries involved. This is purely a deletion task.

## Implementation steps (developer-facing)

1. **Delete `nl_processing/database/cached_service.py`.**

2. **Edit `tests/unit/database/conftest.py`:**
   - Remove the import: `from nl_processing.database.cached_service import CachedDatabaseService`
   - Remove the `cached_service` fixture (lines 167-174):
     ```python
     @pytest.fixture
     def cached_service(monkeypatch: pytest.MonkeyPatch, mock_backend: MockBackend) -> CachedDatabaseService:
         ...
     ```

3. **Edit `tests/unit/database/test_service.py`:**
   - Remove the import: `from nl_processing.database.cached_service import CachedDatabaseService`
   - Update the module docstring from `"""Unit tests for DatabaseService and CachedDatabaseService."""` to `"""Unit tests for DatabaseService."""`
   - Remove the `# ---- CachedDatabaseService ----` section header and all three test functions:
     - `test_cached_service_caches_results`
     - `test_cached_service_clears_on_add`
     - `test_cached_service_no_cache_random`

4. **Edit `vulture_whitelist.py`:**
   - Remove the import line: `from nl_processing.database.cached_service import CachedDatabaseService`
   - Remove the comment: `# CachedDatabaseService -- wraps DatabaseService with LRU cache (T7)`
   - Remove the three method whitelist lines:
     ```python
     CachedDatabaseService.add_words  # type: ignore[misc]
     CachedDatabaseService.get_words  # type: ignore[misc]
     CachedDatabaseService.create_tables  # type: ignore[misc]
     ```
   - Remove `"CachedDatabaseService"` from the `__all__` list.

5. **Run `make check`** and confirm 100% green.

## Production safety constraints (mandatory)

- **Database operations**: None. This task only deletes code and test files.
- **Resource isolation**: No shared resources involved.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: N/A -- this is pure deletion.
- **Correct libraries only**: N/A.
- **Correct file locations**: Only deleting from existing locations.
- **No regressions**: The deleted tests tested only the deleted class. No other test references `CachedDatabaseService` or `cached_service` fixture outside the files being modified (confirmed via grep).

## Error handling + correctness rules (mandatory)

- N/A -- deletion task. No new error handling paths.

## Zero legacy tolerance rule (mandatory)

This task IS the legacy removal. After completion:
- No `CachedDatabaseService` class exists anywhere in production code.
- No test fixtures or test functions reference it.
- No vulture whitelist entries for it.

## Acceptance criteria (testable)

1. `nl_processing/database/cached_service.py` does not exist on disk.
2. `grep -r "CachedDatabaseService" nl_processing/ tests/` returns zero matches (excluding `.pyc` / `__pycache__`).
3. `grep -r "cached_service" nl_processing/ tests/` returns zero matches related to the deleted class (excluding `.pyc` / `__pycache__`; the `database_cache` product brief mentioning the name in prose is acceptable).
4. `vulture_whitelist.py` contains no `CachedDatabaseService` references.
5. `make check` is 100% green.

## Verification / quality gates

- [ ] `nl_processing/database/cached_service.py` deleted
- [ ] `tests/unit/database/conftest.py` updated (fixture removed)
- [ ] `tests/unit/database/test_service.py` updated (3 tests removed)
- [ ] `vulture_whitelist.py` updated (6 lines removed)
- [ ] `make check` passes (ruff format, ruff check, pylint, vulture, jscpd, unit tests, integration tests, e2e tests)
- [ ] No new warnings introduced

## Edge cases

- **Import cycle check**: `cached_service.py` imports from `service.py` but nothing imports from `cached_service.py` (except tests and vulture whitelist, which are being updated). No cycle to worry about.
- **`__init__.py` exports**: `nl_processing/database/__init__.py` is empty, so no re-exports to clean up.

## Notes / risks

- **Risk**: Something outside the known files imports `CachedDatabaseService`.
  - **Mitigation**: Full-repo grep confirmed only `tests/unit/database/conftest.py`, `tests/unit/database/test_service.py`, `vulture_whitelist.py`, `README.md`, `docs/planning-artifacts/architecture.md`, and old sprint docs reference it. README and shared architecture are out of scope (they are shared infra/docs, not this module's responsibility). Old sprint docs are historical artifacts, not executed code.
