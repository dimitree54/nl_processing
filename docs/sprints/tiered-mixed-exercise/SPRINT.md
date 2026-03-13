---
Sprint ID: `2026-03-14_tiered-mixed-exercise`
Sprint Goal: Implement the Tiered Mixed-Exercise Extension across `core`, `database`, `database_cache`, and `sampling` packages.
Sprint Type: module
Module: core, database, database_cache, sampling
---

## Goal

Add the tiered mixed-exercise mode as an additive surface across four packages: shared DTOs and provider contract in `core`, a `TieredExerciseProgressStore` with dedicated repeat-state table in `database`, a `TieredExerciseCacheService` with local SQLite tiered schema in `database_cache`, and a `TieredExerciseSampler` with ordered-tier exercise selection in `sampling`. All existing behavior remains untouched.

## Module Scope

### What this sprint implements

- **`core`** -- Shared tiered DTOs (`TieredCandidate`, `TieredExerciseSelection`) and provider protocol (`TieredCandidateProvider`) to prevent circular dependencies between `database`, `database_cache`, and `sampling`.
- **`database`** -- `TieredExerciseProgressStore` with dedicated `user_word_tiered_repeat_state_<src>_<tgt>` table, tiered candidate reads, mixed progress summary, atomic tiered answer replay, and tiered snapshot export.
- **`database_cache`** -- `TieredExerciseCacheService` with local SQLite schema for tiered snapshot, repeat-state mirror, tiered outbox, refresh/flush, and local tiered progress summary.
- **`sampling`** -- `TieredExerciseSampler` with ordered exercise tiers, finished-word weighting, repeat-mode-aware exercise selection.

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED -- this sprint may ONLY touch:**

- `packages/core/src/nl_processing/core/` -- add tiered models and ports
- `packages/core/tests/` -- add tiered model/port unit tests
- `packages/database/src/nl_processing/database/` -- add tiered store and backend extensions
- `packages/database/tests/` -- add tiered tests
- `packages/database_cache/src/nl_processing/database_cache/` -- add tiered cache service and local store extensions
- `packages/database_cache/tests/` -- add tiered tests
- `packages/sampling/src/nl_processing/sampling/` -- add tiered sampler
- `packages/sampling/tests/` -- add tiered tests

**FORBIDDEN -- this sprint must NEVER touch:**

- `docs/requirements/`, `docs/architecture/`, any `docs/module-spec.md`
- `packages/translate_word/`, `packages/translate_text*/`, `packages/extract_*/`
- Root configs (`Makefile`, `pyproject.toml`, `ruff.toml`) -- already correct
- Any bot-level code or handlers
- Existing `ExerciseProgressStore`, `DatabaseCacheService`, or `WordSampler` behavior

### Test Scope

- **`core`**: `make -C packages/core check`
- **`database`**: `make -C packages/database check`
- **`database_cache`**: `make -C packages/database_cache check`
- **`sampling`**: `make -C packages/sampling check`
- **NEVER run** the global `make check` during individual task verification.

## Interface Contract

### Public interfaces this sprint adds

```python
# core -- shared tiered models
class TieredCandidate(BaseModel):
    pair: WordPair
    source_word_id: int
    scores: dict[str, int]          # ordered exercise scores
    in_repeat_mode: bool

class TieredExerciseSelection(BaseModel):
    pair: WordPair
    source_word_id: int
    exercise_type: str
    in_repeat_mode: bool

# core -- shared tiered provider protocol
@runtime_checkable
class TieredCandidateProvider(Protocol):
    async def get_tiered_candidates(self) -> list[TieredCandidate]: ...

# database
class TieredExerciseProgressStore:
    def __init__(self, *, user_id, source_language, target_language,
                 mode_slug, exercise_types, backend?): ...
    async def get_tiered_candidates(self) -> list[TieredCandidate]: ...
    async def get_tiered_progress_summary(self) -> TieredProgressSummary: ...
    async def apply_tiered_result(self, *, event_id, source_word_id,
                                  exercise_type, delta) -> None: ...
    async def export_tiered_snapshot(self) -> list[TieredSnapshotEntry]: ...

# database_cache
class TieredExerciseCacheService:
    def __init__(self, *, user_id, source_language, target_language,
                 mode_slug, exercise_types, cache_ttl,
                 remote_tiered_progress?, local_store?, cache_dir?): ...
    async def init(self) -> CacheStatus: ...
    async def get_tiered_candidates(self) -> list[TieredCandidate]: ...
    async def get_tiered_progress_summary(self) -> TieredProgressSummary: ...
    async def record_tiered_result(self, *, source_word_id, exercise_type,
                                   delta) -> None: ...
    async def refresh(self) -> None: ...
    async def flush(self) -> None: ...
    async def get_status(self) -> CacheStatus: ...

# sampling
class TieredExerciseSampler:
    def __init__(self, *, user_id, source_language, target_language,
                 mode_slug, exercise_types, finished_word_weight?,
                 tiered_store?): ...
    async def sample(self, limit) -> list[TieredExerciseSelection]: ...
```

## Scope

### In

- Shared tiered DTOs and provider protocol in `core`
- Remote tiered repeat-state table creation and CRUD in `database`
- Tiered candidate reads joining scores + repeat-state in `database`
- Mixed progress summary (all-positive rule) in `database` and `database_cache`
- Atomic tiered answer replay (score delta + repeat-state transition) in `database`
- Tiered snapshot export for cache rebuilds in `database`
- Local SQLite tiered schema (snapshot, repeat-state, outbox) in `database_cache`
- Tiered init/refresh/flush lifecycle in `database_cache`
- Tiered sampler with ordered-tier exercise selection in `sampling`
- Finished-word weighting (configurable, default 0.01) in `sampling`
- Repeat-mode-aware exercise choice in `sampling`
- Unit + integration tests for all new surfaces

### Out

- Changes to existing `ExerciseProgressStore`, `DatabaseCacheService`, or `WordSampler`
- New language pairs, new exercise types, or new POS models
- Bot-level integration or handler changes
- Requirements/architecture doc changes

## Inputs (contracts)

- `packages/database/docs/module-spec.md` Section 5 (TFR-DB-1 through TFR-DB-8, TBR-DB-1 through TBR-DB-6)
- `packages/database_cache/docs/module-spec.md` Section 5 (TFR-DC-1 through TFR-DC-7, TBR-DC-1 through TBR-DC-5)
- `packages/sampling/docs/module-spec.md` Section 5 (TFR-1 through TFR-9, TBR-1 through TBR-5)

## Change digest

- **Requirement deltas**: No existing requirements change. Section 5 in each module spec is entirely additive. All existing behavior (ExerciseProgressStore, DatabaseCacheService, WordSampler) must remain unchanged per TFR-DB-8, TFR-DC-7, TFR-9.

## Task list (dependency-aware)

- **T1:** [`TASK_01.md`](TASK_01.md) (depends: --) -- Add shared tiered DTOs and provider protocol to `core`
- **T2:** [`TASK_02.md`](TASK_02.md) (depends: T1) -- Implement `TieredExerciseProgressStore` in `database` with repeat-state table, candidate reads, progress summary, answer replay, and snapshot export
- **T3:** [`TASK_03.md`](TASK_03.md) (depends: T2) -- Implement `TieredExerciseCacheService` in `database_cache` with local tiered schema, init/refresh/flush, candidate reads, and progress summary
- **T4:** [`TASK_04.md`](TASK_04.md) (depends: T1; parallel: yes, with T2 and T3) -- Implement `TieredExerciseSampler` in `sampling` with ordered-tier selection, finished-word weighting, and repeat-mode exercise choice

## Dependency graph (DAG)

```
T1 --> T2 --> T3
T1 --> T4
```

## Execution plan

### Critical path

T1 --> T2 --> T3

### Parallel tracks (lanes)

- **Lane A**: T1, T2, T3 (core contracts, then database, then cache)
- **Lane B**: T4 (sampling -- can start after T1, runs parallel with T2/T3)

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development uses testing/development databases via Doppler-managed `DATABASE_URL`.
- **Shared resource isolation**: Integration/e2e tests run under `doppler run --` which injects test-database credentials. The new `user_word_tiered_repeat_state_nl_ru` table uses `CREATE TABLE IF NOT EXISTS` -- safe for idempotent creation in both dev and test. Cache files use per-user-per-mode file paths with no overlap with production cache files.

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- `make -C packages/core check` passes
- `make -C packages/database check` passes
- `make -C packages/database_cache check` passes
- `make -C packages/sampling check` passes
- Module isolation: no files outside the ALLOWED list were touched
- New public interfaces match the module spec Section 5 contracts
- Existing `ExerciseProgressStore`, `DatabaseCacheService`, and `WordSampler` behavior unchanged
- Zero legacy tolerance: no dead code left behind
- No errors silenced: no empty catch, no blanket try/catch discarding exceptions
- Requirements/architecture docs unchanged
- Production database untouched; all development against testing DB only

## Risks + mitigations

- **Risk**: Tiered repeat-state transition rules could diverge between `database` and `database_cache`.
  - **Mitigation**: Extract transition logic into a shared pure function (in `core` or as a shared test fixture) and test both paths against the same transition matrix.

- **Risk**: `mode_slug` reuse with a different exercise order could corrupt tiered behavior.
  - **Mitigation**: Validate `mode_slug` + ordered exercises at construction time. Store ordered exercises alongside `mode_slug` in metadata and fail fast on mismatch.

- **Risk**: New `core` models could break existing `core` tests or downstream imports.
  - **Mitigation**: New models/ports are purely additive (new files, new exports). No existing model or port is modified.

- **Risk**: The tiered provider contract could create circular dependencies.
  - **Mitigation**: Place the `TieredCandidateProvider` protocol and DTOs in `core`, which is already a dependency of all three packages.

## Sources used

- `packages/database/docs/module-spec.md` (Section 5, lines 294-381)
- `packages/database_cache/docs/module-spec.md` (Section 5, lines 273-359)
- `packages/sampling/docs/module-spec.md` (Section 5, lines 231-324)
- `packages/core/src/nl_processing/core/models.py`
- `packages/core/src/nl_processing/core/ports.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/backend/abstract.py`
- `packages/database/src/nl_processing/database/backend/_queries.py`
- `packages/database/src/nl_processing/database/backend/_neon_exercise.py`
- `packages/database/src/nl_processing/database/backend/neon.py`
- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_queries.py`
- `packages/sampling/src/nl_processing/sampling/service.py`
- `packages/sampling/tests/unit/sampling/conftest.py`
- Root `Makefile`, per-package `Makefile`s

## Contract summary

### What (requirements)

- TFR-DB-1..8: Dedicated tiered remote store, reuse existing score tables, dedicated repeat-state table, tiered candidate reads, mixed progress summary, atomic tiered replay, tiered snapshot export, no regression
- TFR-DC-1..7: Dedicated tiered cache service, local-only warm-path reads, local repeat-state mirror, atomic local writes, refresh/flush lifecycle, mixed progress summary, no regression
- TFR-1..9: Dedicated tiered sampler, ordered exercise types, selection includes exercise type, finished-word weighting, normal/repeat exercise choice rules, stateless ownership, no regression

### How (architecture)

- Additive: new classes alongside existing ones, no widening of legacy APIs
- Shared: tiered DTOs and provider protocol in `core` to prevent circular imports
- Transition matrix: repeat-state rules (TBR-DB-3..6, TBR-DC-1..4) implemented identically in database and cache
- Validation: `mode_slug` + exercise order validated at construction; invalid repeat-state fails fast

## Impact inventory (implementation-facing)

- **`core`**: new `tiered_models.py`, new `tiered_ports.py`, updated `__init__.py`
- **`database`**: new `tiered_progress.py`, new backend methods for repeat-state CRUD, new queries, new models
- **`database_cache`**: new `tiered_cache.py`, new `_tiered_local_store.py`, new `_tiered_queries.py`, new `tiered_sync.py`
- **`sampling`**: new `tiered_sampler.py`
- **External services**: Neon PostgreSQL (new table creation in integration/e2e), SQLite (new local tables)
- **Test directories**: `packages/core/tests/`, `packages/database/tests/`, `packages/database_cache/tests/`, `packages/sampling/tests/`
