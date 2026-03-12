---
Sprint ID: `2026-03-12_personal-vocab`
Sprint Goal: `Deliver personal-vocabulary read, progress summary, delete, and enriched snapshot APIs (FR-7 through FR-10)`
Sprint Type: `module`
Module: `database`
Status: `planning`
Owners: `Developer`
---

## Goal

Implement the four new functional requirements (FR-7, FR-8, FR-9, FR-10) for the `database` module: personal-vocabulary reads with `added_at` and scores, per-exercise progress summaries, single/bulk delete of per-user state, and enriched cache-facing snapshot export. All delivered with full test coverage and `make check` green.

## Module Scope

### What this sprint implements
- Module: `database`
- Module spec: `docs/module-spec.md`

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `src/nl_processing/database/` — module source code
- `tests/unit/database/` — unit tests (mock backend)
- `tests/integration/database/` — integration tests (real Neon DB)
- `tests/e2e/database/` — end-to-end tests
- `docs/sprints/sprint-personal-vocab/` — this sprint's planning files

**FORBIDDEN — this sprint must NEVER touch:**
- `src/nl_processing/core/` or any `core` package file
- Any other module's code or tests
- Bot code, configs, or infrastructure outside this module

### Test Scope
- **Test directories**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- **Test command**: `make check` (runs ruff format, ruff check, pylint, pytest unit, pytest integration, pytest e2e)
- **NEVER run**: Tests from other packages

## Interface Contract

### Public interface this sprint implements

**On `DatabaseService`:**
```python
async def list_personal_words(self) -> list[PersonalWord]:
    """FR-7: Return translated user entries with stable IDs, added_at, and per-exercise scores."""

async def delete_word(self, source_word_id: int) -> None:
    """FR-9: Delete one personal-vocabulary entry (user membership + scores)."""

async def delete_words(self, source_word_ids: list[int]) -> None:
    """FR-9: Delete many personal-vocabulary entries (user membership + scores)."""
```

**On `ExerciseProgressStore`:**
```python
async def get_progress_summary(self) -> dict[str, ExerciseProgressSummary]:
    """FR-8: Per-exercise-type negative-word count, ratio, and percentage."""

async def export_remote_snapshot(self) -> list[EnrichedSnapshot]:
    """FR-10: Enriched snapshot with added_at for cache rebuilds."""
```

### New/modified models (in `database.models`):
```python
class PersonalWord(BaseModel):
    """FR-7: Full personal-vocabulary entry."""
    pair: WordPair
    source_word_id: int
    target_word_id: int
    added_at: datetime
    scores: dict[str, int]

class ExerciseProgressSummary(BaseModel):
    """FR-8: Per-exercise-type progress report."""
    total_words: int
    negative_words: int
    negative_ratio: float
    negative_percentage: float
```

## Scope

### In
- FR-7: `list_personal_words()` API on `DatabaseService`
- FR-8: `get_progress_summary()` API on `ExerciseProgressStore`
- FR-9: `delete_word()` and `delete_words()` APIs on `DatabaseService`
- FR-10: Enriched `export_remote_snapshot()` with `added_at`
- BR-6, BR-7, FM-5, DEC-6, DEC-7, CR-3 compliance
- File decomposition for files that would exceed 200 lines
- Full test coverage (unit, integration, e2e)

### Out
- Changes to `core` package models (read-only dependency)
- Untranslated word support in personal-vocabulary reads
- Migration tooling or admin UIs
- Cache-side implementation changes

## Inputs (contracts)

- Requirements: `docs/module-spec.md` — FR-7 through FR-10, BR-6/7, FM-5, DEC-6/7, CR-3
- Module spec: `docs/module-spec.md`
- Core models: `packages/core/src/nl_processing/core/models.py` (read-only)

## Change digest

- **Requirement deltas**:
  - FR-7: New `list_personal_words()` returning enriched entries with `added_at`, stable IDs, scores
  - FR-8: New `get_progress_summary()` with per-exercise negative-word stats
  - FR-9: New `delete_word()` / `delete_words()` removing per-user state only
  - FR-10: `export_remote_snapshot()` must now include `added_at`
  - BR-6: `added_at` sourced from `user_words.added_at`
  - BR-7: Deletes never touch shared corpus or translation links
  - FM-5: Delete for non-existent ID raises domain error
  - DEC-7: Progress = `negative_words / total_words * 100` per exercise type
  - CR-3: Personal-vocab reads and cache snapshots share ordering and field set

## Task list (dependency-aware)

- **T1:** `TASK_enrich_backend_query_with_added_at.md` (depends: —) — Add `added_at` to backend `get_user_words` query and propagate through backend layer
- **T2:** `TASK_snapshot_with_added_at.md` (depends: T1) — Enrich `export_remote_snapshot()` with `added_at` (FR-10) plus new local enriched snapshot type
- **T3:** `TASK_list_personal_words.md` (depends: T2) — Implement `list_personal_words()` on DatabaseService (FR-7)
- **T4:** `TASK_get_progress_summary.md` (depends: T2) — Implement `get_progress_summary()` on ExerciseProgressStore (FR-8)
- **T5:** `TASK_delete_personal_words.md` (depends: T1) — Implement `delete_word()` and `delete_words()` APIs (FR-9)

## Dependency graph (DAG)

- T1 → T2
- T2 → T3
- T2 → T4
- T1 → T5

## Execution plan

### Critical path
- T1 → T2 → T3

### Parallel tracks (lanes)
- **Lane A** (read path): T1 → T2 → T3
- **Lane B** (summary): T4 (after T2, parallel with T3)
- **Lane C** (delete): T5 (after T1, parallel with T2/T3/T4)

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development uses testing/development databases via `DATABASE_URL` from Doppler env.
- **Shared resource isolation**: Tests use UUID-based data isolation (unique `user_id` per test). Integration tests use advisory locks. No port/socket conflicts.
- **Migration deliverable**: N/A — no schema changes. The `user_words.added_at` column already exists in the table. New queries read it; no DDL needed.

## Definition of Done (DoD)

All items must be true:

- ✅ All 5 tasks completed and verified
- ✅ `make check` passes (ruff format, ruff check, pylint 200-line limit, unit/integration/e2e tests)
- ✅ Module isolation: no files outside the ALLOWED list were touched
- ✅ Public interface matches module spec (FR-7 through FR-10)
- ✅ Zero legacy tolerance (dead code removed; codebase in sync with spec)
- ✅ No errors are silenced (no swallowed exceptions)
- ✅ Requirements/architecture docs unchanged
- ✅ Production database untouched; all development against testing DB only
- ✅ No file exceeds 200 lines

## Risks + mitigations

- **Risk**: `exercise_progress.py` is at 195 lines — adding `get_progress_summary()` will push it over 200.
  - **Mitigation**: T4 must decompose `exercise_progress.py` as part of adding the new method. Extract helper methods or create a new `personal_vocab.py` module.

- **Risk**: `_queries.py` is at 187 lines — new SQL queries for delete and enriched reads will push it over 200.
  - **Mitigation**: T1 and T5 must split `_queries.py` into logical sub-modules (e.g., `_queries_personal.py` or `_queries_delete.py`) as part of adding new queries.

- **Risk**: `neon.py` is at 182 lines — new backend methods for delete will push it over 200.
  - **Mitigation**: T5 must extract new backend operations into a dedicated module (following the `_neon_exercise.py` pattern).

- **Risk**: `WordPairSnapshot` in `core` does not have `added_at` — we cannot modify `core`.
  - **Mitigation**: T2 creates a local `EnrichedWordPairSnapshot` model in `database.models` that extends or wraps `WordPairSnapshot` with `added_at`. This is a local extension, not a core modification.

- **Risk**: `conftest.py` (unit) is at 198 lines — adding mock methods for new backend operations may push it over.
  - **Mitigation**: Extract `MockBackend` into its own file if needed during any task that adds new mock methods.

- **Risk**: `abstract.py` is at 142 lines — adding new abstract methods for delete operations.
  - **Mitigation**: Monitor; 142 + ~20 for delete methods = ~162, still safe.

## Migration plan (if data model changes)

N/A — no data model changes. The `user_words.added_at TIMESTAMP NOT NULL DEFAULT NOW()` column already exists in the production schema.

## Rollback / recovery notes

- All new methods are additive — existing callers are not affected.
- If rollback needed: revert the commits. No schema migration to reverse.

## Task validation status

- Per-task validation order: `T1` → `T2` → `T3` → `T4` → `T5`
- Validator: `task-checker`
- Outcome: `pending`

## Sources used

- Requirements: `docs/module-spec.md`
- Code read:
  - `src/nl_processing/database/service.py` (180 lines)
  - `src/nl_processing/database/exercise_progress.py` (195 lines)
  - `src/nl_processing/database/models.py` (7 lines)
  - `src/nl_processing/database/exceptions.py` (6 lines)
  - `src/nl_processing/database/backend/abstract.py` (142 lines)
  - `src/nl_processing/database/backend/neon.py` (182 lines)
  - `src/nl_processing/database/backend/_queries.py` (187 lines)
  - `src/nl_processing/database/backend/_neon_exercise.py` (119 lines)
  - `src/nl_processing/database/testing.py` (111 lines)
  - `tests/unit/database/conftest.py` (198 lines)
  - `tests/unit/database/test_service.py` (182 lines)
  - `tests/unit/database/test_exercise_progress.py` (163 lines)
  - `tests/integration/database/conftest.py` (38 lines)
  - `tests/integration/database/test_neon_backend.py` (161 lines)
  - `tests/integration/database/test_exercise_scores.py` (139 lines)
  - `tests/integration/database/test_table_creation.py` (129 lines)
  - `tests/e2e/database/conftest.py` (62 lines)
  - `tests/e2e/database/test_exercise_progress.py` (96 lines)
  - `tests/e2e/database/test_user_word_lists.py` (90 lines)
  - `tests/e2e/database/test_word_addition_flow.py` (78 lines)
  - `tests/e2e/database/test_untranslated_words.py` (45 lines)
  - `packages/core/src/nl_processing/core/models.py` (67 lines)

## Contract summary

### What (requirements)
- FR-7: Personal-vocabulary read API with `added_at`, stable IDs, per-exercise scores
- FR-8: Per-exercise progress summary (negative-word percentage)
- FR-9: Delete APIs removing per-user membership and scores only
- FR-10: Enriched snapshot export with `added_at` for cache rebuilds

### How (architecture)
- Extend `get_user_words` SQL query to include `uw.added_at`
- Create local `PersonalWord` and `ExerciseProgressSummary` models in `database.models`
- Create local `EnrichedWordPairSnapshot` model wrapping `WordPairSnapshot` + `added_at`
- Add delete backend methods (new abstract + neon implementation)
- Add new SQL queries for delete operations
- Decompose files approaching 200-line limit as part of feature tasks

## Impact inventory (implementation-facing)

- **Module**: `database` — `src/nl_processing/database/`
- **Interfaces**: `DatabaseService.list_personal_words()`, `DatabaseService.delete_word()`, `DatabaseService.delete_words()`, `ExerciseProgressStore.get_progress_summary()`, `ExerciseProgressStore.export_remote_snapshot()` (enriched)
- **Data model**: No schema changes; new local Pydantic models in `database.models`
- **External services**: Neon PostgreSQL via `asyncpg` (existing)
- **Test directories**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
