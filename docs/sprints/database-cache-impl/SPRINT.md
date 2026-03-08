---
Sprint ID: `2026-03-08_database-cache-impl`
Sprint Goal: Implement the `database_cache` module from scratch and sync all documentation
Sprint Type: module
Module: `database_cache`
Status: planning
---

## Goal

Implement the `database_cache` module — a local-first SQLite cache that accelerates the vocabulary practice loop by serving reads and accepting writes locally, syncing with the remote `database` module in the background. After implementation, update shared project docs to reflect the new module.

## Module Scope

### What this sprint implements
- Module: `database_cache` (local SQLite cache layer in front of remote `database`)
- Architecture spec: `nl_processing/database_cache/docs/architecture_database_cache.md`
- PRD: `nl_processing/database_cache/docs/prd_database_cache.md`

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `nl_processing/database_cache/` — module source code (excluding `docs/` subfolder)
- `tests/unit/database_cache/` — unit tests
- `tests/integration/database_cache/` — integration tests
- `tests/e2e/database_cache/` — E2E tests
- `pyproject.toml` — to add `aiosqlite` dependency
- `vulture_whitelist.py` — to whitelist new public API symbols
- `docs/architecture.md` — to add `database_cache` references (Task 13)
- `docs/prd.md` — to add `database_cache` references (Task 13)
- `nl_processing/database_cache/docs/` — to sync module docs with implementation (Task 14)

**FORBIDDEN — this sprint must NEVER touch:**
- Any other module's code (`database/`, `sampling/`, `core/`, etc.)
- Any other module's tests
- Bot code
- `ruff.toml`, `Makefile`, `.jscpd.json`

### Test Scope
- **Test directories**: `tests/unit/database_cache/`, `tests/integration/database_cache/`, `tests/e2e/database_cache/`
- **Test commands**:
  - Unit: `uv run pytest tests/unit/database_cache/ -x -v`
  - Integration: `uv run pytest tests/integration/database_cache/ -x -v`
  - E2E: `doppler run -- uv run pytest tests/e2e/database_cache/ -x -v`
- **Full quality gate**: `make check` (runs all linters + all test suites)

## Interface Contract

### Public interface this sprint implements

```python
from datetime import timedelta
from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.models import WordPair, ScoredWordPair
from nl_processing.database_cache.service import DatabaseCacheService
from nl_processing.database_cache.models import CacheStatus
from nl_processing.database_cache.exceptions import (
    CacheNotReadyError,
    CacheStorageError,
    CacheSyncError,
)

# Construction
cache = DatabaseCacheService(
    user_id="alex",
    source_language=Language.NL,
    target_language=Language.RU,
    exercise_types=["nl_to_ru", "multiple_choice"],
    cache_ttl=timedelta(minutes=30),
)

# Lifecycle
status: CacheStatus = await cache.init()

# Reads
pairs: list[WordPair] = await cache.get_words(
    word_type=PartOfSpeech.NOUN, limit=10, random=True,
)
scored: list[ScoredWordPair] = await cache.get_word_pairs_with_scores()

# Writes
await cache.record_exercise_result(
    source_word=Word(
        normalized_form="fiets",
        word_type=PartOfSpeech.NOUN,
        language=Language.NL,
    ),
    exercise_type="nl_to_ru",
    delta=-1,
)

# Sync
await cache.refresh()
await cache.flush()

# Status
status: CacheStatus = await cache.get_status()
```

### Remote interface this sprint consumes

```python
from nl_processing.database.exercise_progress import ExerciseProgressStore

# Snapshot export
snapshot: list[ScoredWordPair] = await progress.export_remote_snapshot()

# Idempotent score delta replay
await progress.apply_score_delta(
    event_id="uuid", source_word_id=101,
    exercise_type="nl_to_ru", delta=-1,
)
```

## Scope

### In
- All 7 source files: `__init__.py`, `service.py`, `local_store.py`, `sync.py`, `models.py`, `exceptions.py`, `logging.py`
- 4 SQLite tables: `cached_word_pairs`, `cached_scores`, `pending_score_events`, `cache_metadata`
- Unit tests (in-memory SQLite, mocked remote)
- Integration tests (file-based SQLite, mocked remote)
- E2E tests (file-based SQLite + real Neon DB)
- Vulture whitelist updates
- Shared doc sync (`docs/architecture.md`, `docs/prd.md`)
- Module doc sync (`nl_processing/database_cache/docs/`)

### Out
- Modifying `sampling` to use `database_cache` (separate sprint)
- Distributed multi-device coherence
- Incremental snapshot refresh
- In-memory hot index layer

## Inputs (contracts)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` (FR1–FR32, NFR1–NFR14)
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md`
- Product brief: `nl_processing/database_cache/docs/product-brief-database_cache-2026-03-07.md`
- Remote API: `nl_processing/database/exercise_progress.py` (`ExerciseProgressStore`)
- Shared models: `nl_processing/database/models.py` (`ScoredWordPair`, `WordPair`)
- Shared architecture: `docs/architecture.md` (to update)
- Shared PRD: `docs/prd.md` (to update)

## Change digest

- **Requirement deltas**: No changes to requirements. This sprint implements the fully-written database_cache design docs.
- **Architecture deltas**: No changes to architecture. Shared docs (`docs/architecture.md`, `docs/prd.md`) still reference the old `CachedDatabaseService` and don't mention `database_cache` — Task 13 fixes this.

## Task list (dependency-aware)

- **T1:** `TASK_01_add_aiosqlite_dependency.md` (depends: —) — Add `aiosqlite` to `pyproject.toml`
- **T2:** `TASK_02_exceptions_module.md` (depends: T1) — Create `exceptions.py`
- **T3:** `TASK_03_models_module.md` (depends: T1) — Create `models.py` with `CacheStatus`
- **T4:** `TASK_04_logging_module.md` (depends: T1) — Create `logging.py`
- **T5:** `TASK_05_local_store_module.md` (depends: T1, T2, T3, T4) — Create `local_store.py` (SQLite schema + CRUD)
- **T6:** `TASK_06_sync_module.md` (depends: T5) — Create `sync.py` (refresh/flush orchestration)
- **T7:** `TASK_07_service_module.md` (depends: T5, T6) — Create `service.py` (`DatabaseCacheService`)
- **T8:** `TASK_08_init_module.md` (depends: T7) — Create `__init__.py`
- **T9:** `TASK_09_unit_tests.md` (depends: T8) — Write unit tests
- **T10:** `TASK_10_integration_tests.md` (depends: T9) — Write integration tests
- **T11:** `TASK_11_e2e_tests.md` (depends: T10) — Write E2E tests
- **T12:** `TASK_12_vulture_whitelist.md` (depends: T8) — Update vulture whitelist
- **T13:** `TASK_13_sync_shared_docs.md` (depends: T8) — Update `docs/architecture.md` and `docs/prd.md`
- **T14:** `TASK_14_sync_module_docs.md` (depends: T8) — Review/fix `database_cache/docs/` to match implementation

## Dependency graph (DAG)

```
T1 ──┬── T2 ──┐
     ├── T3 ──┤
     └── T4 ──┼── T5 ── T6 ──┐
              │               ├── T7 ── T8 ──┬── T9 ── T10 ── T11
              │               │              ├── T12
              │               │              ├── T13
              │               │              └── T14
              └───────────────┘
```

## Execution plan

### Critical path
T1 → T5 → T6 → T7 → T8 → T9 → T10 → T11

### Parallel tracks (lanes)

- **Lane A (main)**: T1 → T5 → T6 → T7 → T8 → T9 → T10 → T11
- **Lane B (after T1)**: T2, T3, T4 (can be parallel with each other; must complete before T5)
- **Lane C (after T8)**: T12, T13, T14 (can be parallel with each other and with T9–T11)

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. Unit and integration tests use local SQLite only (no Neon). E2E tests run with `doppler run --` which uses the `dev` Neon database — never production.
- **Shared resource isolation**: SQLite cache files are created per `(user_id, source_language, target_language)` in a configurable local directory. Tests use `tmp_path` (pytest) or `/tmp` — never production paths. No port conflicts (SQLite is file-based, no server).
- **Migration deliverable**: N/A — no remote data model changes. `database_cache` creates its own local SQLite schema; the remote `database` schema is unchanged.

## Definition of Done (DoD)

All items must be true:

- [ ] All 14 tasks completed and verified
- [ ] `make check` passes (ruff, pylint 200-line, vulture, jscpd, all test suites)
- [ ] Module isolation: no files outside the ALLOWED list were touched
- [ ] Public interface matches architecture spec exactly
- [ ] Zero legacy tolerance: shared docs updated to remove `CachedDatabaseService` references and add `database_cache`
- [ ] No errors are silenced (no swallowed exceptions)
- [ ] Production database untouched; all development against dev/test resources only
- [ ] All source files ≤ 200 lines
- [ ] All 7 module source files created and functional

## Risks + mitigations

- **Risk**: `aiosqlite` version incompatibility with Python 3.12+
  - **Mitigation**: T1 includes version verification. `aiosqlite` 0.20+ supports Python 3.12.
- **Risk**: SQLite WAL mode + async access patterns causing lock contention
  - **Mitigation**: Architecture mandates single-refresh / single-flush guards. `aiosqlite` serializes access via a dedicated thread.
- **Risk**: 200-line file limit exceeded in `local_store.py` (SQLite schema + 4 tables + CRUD)
  - **Mitigation**: Architecture already splits sync logic into `sync.py`. If `local_store.py` grows too large, further decomposition is permitted.
- **Risk**: E2E tests require real Neon DB (`dev` environment via Doppler)
  - **Mitigation**: E2E tests run under `doppler run --` which injects `dev` DATABASE_URL. CI pipeline already supports this.

## Rollback / recovery notes

- Module is entirely new — rollback is deleting `nl_processing/database_cache/` source files and `tests/*/database_cache/` directories
- Shared doc updates (T13) can be reverted independently via git
- `pyproject.toml` change (T1) can be reverted by removing the `aiosqlite` line

## Task validation status

- Per-task validation order: T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14
- Validator: self-validated against checklists
- Outcome: approved
- Notes: All tasks reviewed for completeness, module boundary constraints, test scope, and production safety

## Sources used

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md`
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md`
- Product brief: `nl_processing/database_cache/docs/product-brief-database_cache-2026-03-07.md`
- Remote API: `nl_processing/database/exercise_progress.py`
- Shared models: `nl_processing/database/models.py`, `nl_processing/core/models.py`
- Shared docs: `docs/architecture.md`, `docs/prd.md`
- Build config: `pyproject.toml`, `Makefile`, `ruff.toml`, `vulture_whitelist.py`
- Existing test patterns: `tests/unit/database/conftest.py`, `tests/unit/sampling/conftest.py`

## Contract summary

### What (requirements)
- FR1–FR7: Lifecycle — constructor, init, stale-while-revalidate, bootstrap refresh
- FR8–FR13: Local reads — `get_words()`, `get_word_pairs_with_scores()`, CacheNotReadyError
- FR14–FR18: Local writes — `record_exercise_result()`, transactional outbox
- FR19–FR26: Refresh/flush — snapshot rebuild, idempotent replay, concurrency guards
- FR27–FR29: Exercise set management — metadata storage, mismatch detection
- FR30–FR32: Status/observability — `get_status()`, background error logging

### How (architecture)
- SQLite via `aiosqlite` — 4 tables: `cached_word_pairs`, `cached_scores`, `pending_score_events`, `cache_metadata`
- Direct dependency on `ExerciseProgressStore` (no Protocol abstraction)
- Stale-while-revalidate refresh policy
- Transactional outbox pattern for local writes
- Idempotent remote replay via `event_id`
- Atomic snapshot rebuild with pending-event reapply

## Impact inventory (implementation-facing)

- **Module**: `database_cache` (`nl_processing/database_cache/`)
- **Interfaces**: `DatabaseCacheService` with `init()`, `get_words()`, `get_word_pairs_with_scores()`, `record_exercise_result()`, `refresh()`, `flush()`, `get_status()`
- **Data model**: 4 SQLite tables (local only — no remote schema changes)
- **External services**: `database.ExerciseProgressStore` (remote Neon, consumed not modified)
- **Test directories**: `tests/unit/database_cache/`, `tests/integration/database_cache/`, `tests/e2e/database_cache/`
