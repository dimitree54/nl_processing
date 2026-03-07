---
Sprint ID: `2026-03-07_database-exercise-tables`
Sprint Goal: `Refactor exercise progress to per-exercise-type tables, fix pre-existing test failure, add cache-support APIs, and mark cached_service.py as legacy.`
Sprint Type: `module`
Module: `database`
Status: `planning`
---

## Goal

Refactor the database module so exercise scores are stored in **per-exercise-type tables** instead of one shared table, update the `ExerciseProgressStore` constructor/API, add cache-support APIs (`export_remote_snapshot`, `apply_score_delta` with idempotency tracking), fix the pre-existing failing test in `test_service.py`, and mark `cached_service.py` as legacy. All changes must keep `make check` green and respect the 200-line file limit.

## Module Scope

### What this sprint implements
- Module: `database` (`nl_processing/database/`)
- Prior sprint: `docs/sprints/database-and-sampling/SPRINT.md` (original build-out)

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `nl_processing/database/` — module source code (all files within)
- `tests/unit/database/` — unit tests
- `tests/integration/database/` — integration tests
- `tests/e2e/database/` — e2e tests
- `vulture_whitelist.py` — vulture false-positive whitelist (only to add/update entries for new/changed public APIs)

**FORBIDDEN — this sprint must NEVER touch:**
- `nl_processing/sampling/` — sampling module code (downstream consumer; its adaptation is a separate sprint)
- `nl_processing/core/` — core models
- Any bot-level code
- `docs/requirements/`, `docs/architecture/`
- Any other module's code or tests

### Test Scope
- **Test directories**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- **Test commands**:
  - Unit: `uv run pytest tests/unit/database/ -x -v`
  - Integration: `doppler run -- uv run pytest tests/integration/database/ -x -v`
  - E2E: `doppler run -- uv run pytest tests/e2e/database/ -x -v`
- **NEVER run**: `uv run pytest` (full suite) or tests from other modules

## Interface Contract

### Public interface changes this sprint implements

```python
# ExerciseProgressStore — CHANGED constructor + method signatures
class ExerciseProgressStore:
    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language,
        target_language: Language,
        exercise_types: list[str],          # NEW — required, non-empty
    ) -> None: ...

    async def increment(
        self,
        source_word_id: int,                # CHANGED — was source_word: Word
        exercise_type: str,
        delta: int,
    ) -> None: ...

    async def get_word_pairs_with_scores(    # CHANGED — no longer takes exercise_types param
        self,
    ) -> list[ScoredWordPair]: ...

    # NEW — cache-support APIs
    async def export_remote_snapshot(
        self,
    ) -> list[ScoredWordPair]: ...

    async def apply_score_delta(
        self,
        event_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None: ...
```

### Downstream impact (NOT addressed in this sprint)
- `nl_processing/sampling/service.py` constructs `ExerciseProgressStore` without `exercise_types` and calls `get_word_pairs_with_scores(self._exercise_types)`. This will break. A **separate sprint** must update the sampling module.

## Scope

### In
- T1: Fix pre-existing failing test (`test_add_words_uses_word_language_for_storage`)
- T2: Update SQL query templates for per-exercise-type tables + applied_events table
- T3: Update `AbstractBackend` with new/changed methods for per-exercise-type tables and event tracking
- T4: Update `NeonBackend` to implement new abstract methods
- T5: Refactor `ExerciseProgressStore` — new constructor, changed API, per-exercise-type table logic
- T6: Add cache-support APIs (`export_remote_snapshot`, `apply_score_delta` with idempotency)
- T7: Mark `cached_service.py` as legacy
- T8: Update `testing.py` for per-exercise-type table drop/reset
- T9: Update unit tests (MockBackend, test fixtures, all ExerciseProgressStore tests)
- T10: Update integration tests (table creation, exercise scores)
- T11: Update e2e tests (exercise progress)
- T12: Update `vulture_whitelist.py` for new/changed APIs

### Out
- Sampling module updates (separate sprint — `nl_processing/sampling/` is FORBIDDEN)
- Bot-level changes
- `database_cache` module implementation (this sprint only adds the APIs it will consume)
- Production database migration execution (delivered as `MIGRATION_PLAN.md`)

## Inputs (contracts)

- Requirements: User-provided change summary (this sprint request)
- Architecture: User-provided change summary (this sprint request)
- Prior sprint: `docs/sprints/database-and-sampling/SPRINT.md`
- Prototype codebase: current state of `nl_processing/database/` and tests

## Change digest

- **Requirement deltas**:
  - Exercise score tables split from single `user_word_exercise_scores_{src}_{tgt}` to per-exercise-type `user_word_exercise_scores_{src}_{tgt}_{exercise_slug}`
  - `ExerciseProgressStore` constructor now requires `exercise_types: list[str]` (non-empty)
  - `increment()` takes `source_word_id: int` instead of `source_word: Word`
  - `get_word_pairs_with_scores()` no longer accepts `exercise_types` param (uses configured set)
  - New cache-support APIs: `export_remote_snapshot()`, `apply_score_delta()` with idempotency
  - `cached_service.py` marked as legacy
  - Fix failing test `test_add_words_uses_word_language_for_storage`

- **Architecture deltas**:
  - New table naming: `user_word_exercise_scores_{src}_{tgt}_{exercise_slug}`
  - New `applied_events` table (or per-pair variant) for idempotency tracking
  - `cached_service.py` annotated as "legacy prototype helper; superseded by planned database_cache module"

## Task list (dependency-aware)

- **T1:** `TASK_01_fix_add_words_language_bug.md` (depends: —) — Fix pre-existing test failure: `add_words` must use `word.language` for storage table
- **T2:** `TASK_02_sql_queries_per_exercise_tables.md` (depends: T1) — Update `_queries.py` with per-exercise-type table DDL, score queries, and applied_events table
- **T3:** `TASK_03_abstract_backend_new_methods.md` (depends: T2) — Update `AbstractBackend` with new/changed abstract methods
- **T4:** `TASK_04_neon_backend_implementation.md` (depends: T3) — Implement new abstract methods in `NeonBackend`
- **T5:** `TASK_05_exercise_progress_refactor.md` (depends: T4) — Refactor `ExerciseProgressStore`: new constructor, changed `increment`/`get_word_pairs_with_scores`
- **T6:** `TASK_06_cache_support_apis.md` (depends: T5) — Add `export_remote_snapshot()` and `apply_score_delta()` to `ExerciseProgressStore`
- **T7:** `TASK_07_mark_cached_service_legacy.md` (depends: T1) (parallel: yes, with T2–T6) — Mark `cached_service.py` as legacy
- **T8:** `TASK_08_update_testing_utilities.md` (depends: T4) — Update `testing.py` for per-exercise-type table drop/reset
- **T9:** `TASK_09_update_unit_tests.md` (depends: T6, T7, T8) — Update MockBackend, unit test fixtures, and all unit tests
- **T10:** `TASK_10_update_integration_tests.md` (depends: T8, T9) — Update integration tests for per-exercise-type tables
- **T11:** `TASK_11_update_e2e_tests.md` (depends: T10) — Update e2e tests for new API signatures
- **T12:** `TASK_12_update_vulture_whitelist.md` (depends: T11) — Update `vulture_whitelist.py` for new/changed APIs

## Dependency graph (DAG)

```
T1 → T2 → T3 → T4 → T5 → T6 ─┐
                                ├→ T9 → T10 → T11 → T12
T1 → T7 (parallel with T2-T6) ─┤
T4 → T8 ────────────────────────┘
```

## Execution plan

### Critical path
T1 → T2 → T3 → T4 → T5 → T6 → T9 → T10 → T11 → T12

### Parallel tracks (lanes)
- **Lane A (main)**: T1, T2, T3, T4, T5, T6
- **Lane B (legacy mark)**: T7 (after T1, parallel with T2–T6)
- **Lane C (test utilities)**: T8 (after T4, parallel with T5–T6)
- All lanes converge at T9

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development uses testing/development databases via Doppler-injected `DATABASE_URL`.
- **Shared resource isolation**: Integration and e2e tests use Doppler (`doppler run --`) for isolated test database credentials. Unit tests use `MockBackend` (no DB connection).
- **Migration deliverable**: `docs/sprints/database-exercise-tables/MIGRATION_PLAN.md` — covers creating per-exercise-type tables and `applied_events` table in production, plus data migration from the old shared table.

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- Unit tests pass: `uv run pytest tests/unit/database/ -x -v`
- Integration tests pass: `doppler run -- uv run pytest tests/integration/database/ -x -v`
- E2E tests pass: `doppler run -- uv run pytest tests/e2e/database/ -x -v`
- `make check` passes (all 8 steps green)
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches the contract specified above
- Zero legacy tolerance — old single-table code paths fully removed; `cached_service.py` marked legacy
- No errors are silenced (no swallowed exceptions)
- No file exceeds 200 lines
- Production database untouched; all development against testing DB only
- Migration plan delivered (`MIGRATION_PLAN.md`)

## Risks + mitigations

- **Risk**: `nl_processing/sampling/service.py` calls `ExerciseProgressStore` with old constructor (no `exercise_types`) and passes `exercise_types` to `get_word_pairs_with_scores()`. After this sprint, those calls will break.
  - **Mitigation**: This sprint does NOT touch `sampling/`. A follow-up sprint must update `sampling/service.py` to pass `exercise_types` to the constructor and remove the argument from `get_word_pairs_with_scores()`. Document this clearly in T5. Until then, `sampling` tests will fail — those tests are NOT run by this sprint.

- **Risk**: Per-exercise-type tables create more SQL DDL statements, potentially pushing `_queries.py` over 200 lines.
  - **Mitigation**: Monitor line count in T2. If needed, split into `_queries.py` (word/translation queries) and `_exercise_queries.py` (exercise score queries).

- **Risk**: `NeonBackend.create_tables()` signature change (needs `exercise_types` parameter) could push `neon.py` past 200 lines.
  - **Mitigation**: The new `create_tables` accepts exercise slugs. Keep method implementations concise. Split if needed.

- **Risk**: Production data migration from single table to per-exercise tables could lose data if done incorrectly.
  - **Mitigation**: `MIGRATION_PLAN.md` includes rollback steps, backup instructions, and validation queries. Migration is user-reviewed, never auto-executed.

## Migration plan (if data model changes)

Path: `docs/sprints/database-exercise-tables/MIGRATION_PLAN.md`

## Rollback / recovery notes

- Revert all commits from this sprint (one per task).
- Production migration (if applied) can be rolled back per `MIGRATION_PLAN.md` instructions.
- `sampling` module was not touched — no rollback needed there.

## Task validation status

- Per-task validation order: T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12
- Validator: self-validate + task-checker
- Outcome: pending
- Notes: —

## Sources used

- Requirements: User-provided sprint planning request (change summary)
- Architecture: User-provided sprint planning request (change summary)
- Code read (for scoping):
  - `nl_processing/database/backend/_queries.py` (149 lines)
  - `nl_processing/database/backend/abstract.py` (95 lines)
  - `nl_processing/database/backend/neon.py` (184 lines)
  - `nl_processing/database/exercise_progress.py` (135 lines)
  - `nl_processing/database/models.py` (18 lines)
  - `nl_processing/database/testing.py` (104 lines)
  - `nl_processing/database/service.py` (150 lines)
  - `nl_processing/database/cached_service.py` (74 lines)
  - `nl_processing/database/exceptions.py` (6 lines)
  - `nl_processing/database/logging.py` (5 lines)
  - `nl_processing/sampling/service.py` (104 lines) — downstream consumer
  - `tests/unit/database/conftest.py` (169 lines)
  - `tests/unit/database/test_exercise_progress.py` (108 lines)
  - `tests/unit/database/test_service.py` (160 lines)
  - `tests/integration/database/conftest.py` (37 lines)
  - `tests/integration/database/test_exercise_scores.py` (152 lines)
  - `tests/integration/database/test_table_creation.py` (125 lines)
  - `tests/integration/database/test_neon_backend.py` (161 lines)
  - `tests/e2e/database/conftest.py` (50 lines)
  - `tests/e2e/database/test_exercise_progress.py` (95 lines)
  - `vulture_whitelist.py` (116 lines)
  - `Makefile` (10 lines)
  - `pyproject.toml` (38 lines)

## Contract summary

### What (requirements)
- Split single exercise score table into per-exercise-type tables
- Change `ExerciseProgressStore` constructor to require `exercise_types`
- Change `increment()` parameter from `source_word: Word` to `source_word_id: int`
- Remove `exercise_types` parameter from `get_word_pairs_with_scores()`
- Add cache-support APIs: `export_remote_snapshot()`, `apply_score_delta()` with idempotency
- Mark `cached_service.py` as legacy
- Fix pre-existing test failure

### How (architecture)
- Per-exercise-type table naming: `user_word_exercise_scores_{src}_{tgt}_{exercise_slug}`
- `applied_events` table for idempotency tracking (event_id deduplication)
- Backend layer gets new abstract + concrete methods for per-exercise-type operations
- `ExerciseProgressStore` manages multiple tables based on configured `exercise_types`

## Impact inventory (implementation-facing)

- **Module**: `database` (`nl_processing/database/`)
- **Interfaces**: `ExerciseProgressStore` (constructor, `increment`, `get_word_pairs_with_scores`, `export_remote_snapshot`, `apply_score_delta`)
- **Data model**: per-exercise-type score tables, `applied_events` table
- **External services**: Neon PostgreSQL (via `asyncpg`)
- **Test directories**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
