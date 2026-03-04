---
Sprint ID: `2026-03-04_database-and-sampling`
Sprint Goal: `Implement the database persistence module and sampling module from scratch, fully tested against real Neon PostgreSQL.`
Sprint Type: `module`
Module: `database + sampling`
Status: `planning`
Owners: `Developer`
---

## Goal

Deliver fully working `database` and `sampling` modules as specified in architecture docs. The `database` module provides async persistence for words, translations, user word lists, and exercise progress scores via Neon PostgreSQL. The `sampling` module provides weighted and adversarial word sampling for practice sessions. Both modules must pass `make check` after every task.

## Module Scope

### What this sprint implements

- Module: `database` — async persistence layer (DatabaseService, CachedDatabaseService, NeonBackend, ExerciseProgressStore)
- Module: `sampling` — weighted word sampler (WordSampler)
- Architecture specs:
  - `nl_processing/database/docs/architecture_database.md`
  - `nl_processing/sampling/docs/architecture_sampling.md`
  - `docs/planning-artifacts/architecture.md` (shared patterns)

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**

- `nl_processing/database/` — database module source code
- `nl_processing/sampling/` — sampling module source code
- `tests/unit/database/` — database unit tests
- `tests/integration/database/` — database integration tests
- `tests/e2e/database/` — database e2e tests
- `tests/unit/sampling/` — sampling unit tests
- `tests/integration/sampling/` — sampling integration tests
- `pyproject.toml` — add `asyncpg` dependency
- `vulture_whitelist.py` — remove old `save_translation` entry, add new entries as needed

**FORBIDDEN — this sprint must NEVER touch:**

- Any other module's code (`core/`, `extract_text_from_image/`, `extract_words_from_text/`, `translate_text/`, `translate_word/`)
- Any other module's tests
- Bot code
- `docs/requirements/`, `docs/architecture/`, or module doc files
- Makefile, ruff.toml, pytest.ini, .jscpd.json (unless a task explicitly requires it and documents why)

### Test Scope

- **Database test directories**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- **Sampling test directories**: `tests/unit/sampling/`, `tests/integration/sampling/`
- **Test command**: `make check` (runs full suite including all existing 26 tests + new tests)
- Integration/e2e tests require `doppler run --` (already configured in Makefile)

## Interface Contract

### Public interface — database module

```python
# nl_processing/database/service.py
class DatabaseService:
    def __init__(self, *, user_id: str, source_language: Language = Language.NL, target_language: Language = Language.RU) -> None: ...
    async def add_words(self, words: list[Word]) -> AddWordsResult: ...
    async def get_words(self, *, word_type: PartOfSpeech | None = None, limit: int | None = None, random: bool = False) -> list[WordPair]: ...
    @classmethod
    async def create_tables(cls) -> None: ...

class CachedDatabaseService:  # wraps DatabaseService
    ...

# nl_processing/database/exercise_progress.py
class ExerciseProgressStore:
    def __init__(self, *, user_id: str, source_language: Language, target_language: Language) -> None: ...
    async def increment(self, source_word: Word, exercise_type: str, delta: int) -> None: ...
    async def get_word_pairs_with_scores(self, exercise_types: list[str]) -> list[ScoredWordPair]: ...
```

### Public interface — sampling module

```python
# nl_processing/sampling/service.py
class WordSampler:
    def __init__(self, *, user_id: str, source_language: Language = Language.NL, target_language: Language = Language.RU,
                 exercise_types: list[str], positive_balance_weight: float = 0.01) -> None: ...
    async def sample(self, limit: int) -> list[WordPair]: ...
    async def sample_adversarial(self, source_word: Word, limit: int) -> list[WordPair]: ...
```

## Scope

### In

- `asyncpg` added to `pyproject.toml` dependencies
- Database module: exceptions, models, logging, abstract backend, Neon backend, service, cached service, exercise progress store, testing utilities
- Sampling module: WordSampler with weighted and adversarial sampling
- Unit tests for both modules (mocked backends)
- Integration tests for both modules (real Neon database)
- E2e tests for database module (full flow with real translation)
- Legacy cleanup: remove `save_translation` placeholder and its vulture whitelist entry

### Out

- Database migrations tooling
- Additional language pairs beyond NL/RU
- Spaced repetition algorithms
- Bot integration
- CI/CD changes

## Inputs (contracts)

- Requirements: `nl_processing/database/docs/prd_database.md`, `nl_processing/sampling/docs/prd_sampling.md`
- Architecture: `nl_processing/database/docs/architecture_database.md`, `nl_processing/sampling/docs/architecture_sampling.md`
- Shared architecture: `docs/planning-artifacts/architecture.md`
- Product briefs: `nl_processing/database/docs/product-brief-database-2026-03-02.md`, `nl_processing/sampling/docs/product-brief-sampling-2026-03-04.md`

## Change digest

- **Requirement deltas**: None — this is greenfield implementation of documented specs.
- **Architecture deltas**: None — architecture docs are complete and approved.

## Task list (dependency-aware)

- **T1:** `TASK_01_add_asyncpg_dep.md` (depends: —) — Add asyncpg to pyproject.toml
- **T2:** `TASK_02_db_exceptions_models_logging.md` (depends: T1) — Create exceptions.py, models.py, logging.py
- **T3:** `TASK_03_abstract_backend.md` (depends: T2) — Create backend/ with abstract.py ABC
- **T4:** `TASK_04_neon_backend.md` (depends: T3) — Implement NeonBackend (asyncpg)
- **T5:** `TASK_05_database_service.md` (depends: T4) — Implement DatabaseService in service.py (replace save_translation)
- **T6:** `TASK_06_exercise_progress.md` (depends: T5) — Implement ExerciseProgressStore
- **T7:** `TASK_07_cached_service.md` (depends: T5) — Implement CachedDatabaseService
- **T8:** `TASK_08_testing_utilities.md` (depends: T5) — Create testing.py with test helpers
- **T9:** `TASK_09_db_unit_tests.md` (depends: T5, T6) — Unit tests for DatabaseService and ExerciseProgressStore
- **T10:** `TASK_10_db_integration_tests.md` (depends: T8) — Integration tests against real Neon DB
- **T11:** `TASK_11_db_e2e_tests.md` (depends: T10) — E2e tests with real translation flow
- **T12:** `TASK_12_sampling_service.md` (depends: T6) — Implement WordSampler
- **T13:** `TASK_13_sampling_unit_tests.md` (depends: T12) — Unit tests for WordSampler
- **T14:** `TASK_14_sampling_integration_tests.md` (depends: T12, T10) — Integration tests for sampling against real DB

## Dependency graph (DAG)

```
T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T9
                              T5 -> T7
                              T5 -> T8 -> T10 -> T11
                                    T6 -> T9
                                    T6 -> T12 -> T13
                              T10 + T12 -> T14
```

## Execution plan

### Critical path

T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T12 -> T14

### Parallel tracks (lanes)

- **Lane A (foundation)**: T1 -> T2 -> T3 -> T4 -> T5
- **Lane B (post-service)**: T5 -> T7 (CachedDatabaseService, parallel with T6)
- **Lane C (post-service)**: T5 -> T8 (testing.py, parallel with T6 and T7)
- **Lane D (exercise progress)**: T5 -> T6 -> T9 (unit tests, parallel with T10)
- **Lane E (integration)**: T8 -> T10 -> T11
- **Lane F (sampling)**: T6 -> T12 -> T13 (parallel with T10)
- **Lane G (sampling integration)**: T10 + T12 -> T14

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development and testing uses the `dev` Doppler environment which points to `nl_processing_dev` Neon database.
- **Shared resource isolation**: Dev database connection string comes from `doppler run --` with the `dev` environment. Production uses the `prd` environment with a separate database. No port or file path collisions — database access is remote (Neon serverless).
- **Migration deliverable**: `docs/sprints/database-and-sampling/MIGRATION_PLAN.md` — table creation uses `IF NOT EXISTS` semantics; production tables can be created safely via `create_tables()`.

## Definition of Done (DoD)

All items must be true:

- All 14 tasks completed and verified
- `make check` passes (all existing 26 tests + all new tests)
- Module isolation: no files outside the ALLOWED list were touched
- Public interfaces match architecture spec exactly
- Zero legacy tolerance: `save_translation` removed, vulture whitelist cleaned
- No errors are silenced (no swallowed exceptions, except fire-and-forget translation which logs warnings per spec)
- Requirements/architecture docs unchanged
- Production database untouched; all development against dev Neon database only
- No shared local resources conflict with production instance

## Risks + mitigations

- **Risk**: Neon PostgreSQL latency exceeds 200ms threshold from dev machine.
  - **Mitigation**: Integration test T10 includes latency benchmark. If exceeded, report to Dima per architecture spec — abstract backend makes swapping feasible.
- **Risk**: `asyncpg` version incompatibility or Neon-specific connection issues.
  - **Mitigation**: T4 (NeonBackend) tests connection immediately. asyncpg 0.31.0 is stable and supports PostgreSQL via Neon.
- **Risk**: Fire-and-forget translation tasks may leak or cause test instability.
  - **Mitigation**: Unit tests mock translate_word entirely. E2e tests wait for translations explicitly. Background task errors are logged, never raised.
- **Risk**: 200-line file limit exceeded for complex files (service.py, neon.py).
  - **Mitigation**: Architecture already decomposes into many small files. Each task specifies line-count awareness.
- **Risk**: jscpd flags code duplication between test files or between backend methods.
  - **Mitigation**: Extract shared test fixtures into conftest.py. Backend SQL queries are inherently different per method.

## Migration plan

Path: `docs/sprints/database-and-sampling/MIGRATION_PLAN.md`

## Rollback / recovery notes

- All database module code is new — rollback = revert the commits and remove test directories
- `create_tables()` uses `IF NOT EXISTS` — safe to run in any environment
- `drop_all_tables()` in testing.py is irreversible but only runs against dev database via `doppler run --`

## Task validation status

- Per-task validation order: T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T7 -> T8 -> T9 -> T10 -> T11 -> T12 -> T13 -> T14
- Validator: self-validated against checklists A-G
- Outcome: approved
- Notes: All tasks designed for `make check` green after each completion

## Sources used

- Requirements: `nl_processing/database/docs/prd_database.md`, `nl_processing/sampling/docs/prd_sampling.md`
- Architecture: `nl_processing/database/docs/architecture_database.md`, `nl_processing/sampling/docs/architecture_sampling.md`, `docs/planning-artifacts/architecture.md`
- Product briefs: `nl_processing/database/docs/product-brief-database-2026-03-02.md`, `nl_processing/sampling/docs/product-brief-sampling-2026-03-04.md`
- Code read: `nl_processing/database/service.py`, `nl_processing/database/__init__.py`, `nl_processing/sampling/`, `nl_processing/core/models.py`, `nl_processing/core/exceptions.py`, `nl_processing/translate_word/service.py`, `vulture_whitelist.py`, `pyproject.toml`, `Makefile`, `ruff.toml`, `pytest.ini`, `.jscpd.json`, `tests/conftest.py`, existing test files

## Contract summary

### What (requirements)

- Async persistence for words, translations, user word lists, exercise scores (database)
- Weighted sampling of practice items based on exercise performance (sampling)
- Fire-and-forget translation of new words via translate_word
- 200ms latency ceiling for database operations
- Test utilities for dev database setup/teardown

### How (architecture)

- Abstract backend ABC -> NeonBackend (asyncpg) -> DatabaseService -> CachedDatabaseService
- ExerciseProgressStore for per-user per-exercise scores
- Per-language word tables, per-pair translation link tables, user_words junction, exercise score tables
- WordSampler reads from ExerciseProgressStore, applies v1 weighting rule
- All public methods async, environment variables via `os.environ[]`

## Impact inventory (implementation-facing)

- **Module**: `database` (`nl_processing/database/`)
- **Interfaces**: DatabaseService, CachedDatabaseService, ExerciseProgressStore
- **Data model**: words_{lang}, translations_{src}_{tgt}, user_words, user_word_exercise_scores_{src}_{tgt}
- **External services**: Neon PostgreSQL (via asyncpg), translate_word (internal module)
- **Test directories**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`, `tests/unit/sampling/`, `tests/integration/sampling/`

- **Module**: `sampling` (`nl_processing/sampling/`)
- **Interfaces**: WordSampler
- **Data model**: None (reads from database)
- **External services**: database module (ExerciseProgressStore)
- **Test directories**: `tests/unit/sampling/`, `tests/integration/sampling/`
