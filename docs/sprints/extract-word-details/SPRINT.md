---
Sprint ID: `2026-03-13_extract-word-details`
Sprint Goal: Implement `extract_word_details` from scratch and extend `database` + `database_cache` with detailed-word persistence and caching.
Sprint Type: module
Module: extract_word_details, database, database_cache
---

## Goal

Fully implement the `extract_word_details` module (greenfield), add `DetailedWordStore` to `database` (FR-11..FR-14), and add `DetailedWordCacheService` to `database_cache` (FR-11..FR-15). At sprint end, all three module specs must be 100% in sync with their implementations.

## Module Scope

### What this sprint implements

- **`extract_word_details`** — new package from scratch: package scaffold, POS-specific NL->RU detailed models, schema registry, prompt assets per POS, `WordDetailsExtractor` service, unit/integration/e2e tests.
- **`database`** — new `DetailedWordStore` class, new backend abstract + concrete methods for detailed-word CRUD, new SQL queries, updated `create_tables()`, unit/integration/e2e tests.
- **`database_cache`** — new `DetailedWordCacheService` class, pair-scoped local SQLite store, schema-version invalidation, unit/integration/e2e tests.

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**

- `packages/extract_word_details/` — new module (all files created from scratch)
- `packages/database/src/nl_processing/database/` — add `DetailedWordStore` + backend methods
- `packages/database/tests/` — add detailed-word tests
- `packages/database_cache/src/nl_processing/database_cache/` — add `DetailedWordCacheService`
- `packages/database_cache/tests/` — add detailed-word cache tests
- Root `Makefile` — add `extract_word_details` to `PACKAGES` list
- Root `pyproject.toml` — register `extract_word_details` package paths
- Root `ruff.toml` — add `extract_word_details` src path

**FORBIDDEN — this sprint must NEVER touch:**

- `packages/core/` — shared types/models (already sufficient)
- `packages/translate_word/` — separate translation module
- `packages/sampling/` — downstream consumer
- Any other package under `packages/`
- Any bot-level code or handlers

### Test Scope

- **`extract_word_details`**: `packages/extract_word_details/tests/` — `make check` in `packages/extract_word_details/`
- **`database`**: `packages/database/tests/` — `make check` in `packages/database/`
- **`database_cache`**: `packages/database_cache/tests/` — `make check` in `packages/database_cache/`
- **NEVER run** the global `make check` during individual task verification — only the affected package's `make check`.

## Interface Contract

### Public interfaces this sprint implements

```python
# extract_word_details
class WordDetailsExtractor:
    def __init__(self, *, source_language: Language, target_language: Language,
                 model: str, reasoning_effort: str | None, temperature: float | None) -> None: ...
    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]: ...

# database
class DetailedWordStore:
    def __init__(self, *, source_language: Language, target_language: Language,
                 backend: AbstractBackend | None = None,
                 extractor: DetailedWordExtractorPort | None = None) -> None: ...
    async def get_details(self, words: list[Word]) -> list[DetailedWordRecord]: ...
    async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]: ...

# database_cache
class DetailedWordCacheService:
    def __init__(self, *, source_language: Language, target_language: Language,
                 remote_store: ... | None = None,
                 local_store: ... | None = None,
                 cache_dir: str | None = None) -> None: ...
    async def get_or_fetch_details(self, words: list[Word]) -> list[DetailedWordRecord]: ...
```

## Scope

### In

- `extract_word_details` package scaffold (pyproject.toml, Makefile, pytest.ini, ruff.toml, directory structure)
- Root config updates (Makefile PACKAGES, pyproject.toml, ruff.toml)
- POS-specific NL->RU Pydantic detailed models for all 13 Dutch POS values
- Versioned schema registry and serializer contract
- Prompt generator scripts and generated prompt JSON per POS with few-shot examples
- `WordDetailsExtractor` service with POS-based dispatch
- `DetailedWordStore` with backend CRUD, SQL queries, and `create_tables()` update
- `DetailedWordCacheService` with pair-scoped SQLite and schema-version invalidation
- Unit, integration, and e2e tests for all three modules

### Out

- Language pairs beyond `nl -> ru`
- User-specific annotations or progress on detailed records
- Migration tooling for existing production databases
- Cache eviction policies for detailed-word cache
- Admin dashboards

## Inputs (contracts)

- `extract_word_details` module spec: `packages/extract_word_details/docs/module-spec.md`
- `database` module spec: `packages/database/docs/module-spec.md`
- `database_cache` module spec: `packages/database_cache/docs/module-spec.md`
- Core models: `packages/core/src/nl_processing/core/models.py`
- Existing `translate_word` (pattern reference): `packages/translate_word/`

## Change digest

- **Requirement deltas**: No spec changes. This sprint implements existing FR-1..FR-11 in `extract_word_details`, FR-11..FR-14 in `database`, and FR-11..FR-15 in `database_cache`.

## Task list (dependency-aware)

- **T1:** [`TASK_01.md`](TASK_01.md) (depends: —) — Scaffold `extract_word_details` package + implement core types, schema registry, and serializer contract with unit tests
- **T2:** [`TASK_02.md`](TASK_02.md) (depends: T1) — Implement POS-specific NL->RU models, prompt generator scripts, and generated prompt assets with schema consistency tests
- **T3:** [`TASK_03.md`](TASK_03.md) (depends: T2) — Implement `WordDetailsExtractor` service with POS dispatch, unit tests, and integration/e2e tests
- **T4:** [`TASK_04.md`](TASK_04.md) (depends: T1) (parallel: yes, with T2 and T3) — Implement `DetailedWordStore` + backend methods + SQL queries + `create_tables()` update in `database` with unit/integration/e2e tests
- **T5:** [`TASK_05.md`](TASK_05.md) (depends: T1, T4) — Implement `DetailedWordCacheService` in `database_cache` with pair-scoped SQLite, schema-version invalidation, and unit/integration/e2e tests
- **T6:** [`TASK_06.md`](TASK_06.md) (depends: T1, T2, T3, T4, T5) — Update root configs and run final cross-module validation

## Dependency graph (DAG)

```
T1 → T2 → T3
T1 → T4
T1 + T4 → T5
T1 + T2 + T3 + T4 + T5 → T6
```

## Execution plan

### Critical path

T1 → T2 → T3 → T6

### Parallel tracks (lanes)

- **Lane A (extractor)**: T1, T2, T3
- **Lane B (database)**: T4 (can start after T1 completes, parallel with T2/T3)
- **Lane C (cache)**: T5 (starts after T1 + T4)
- **Lane D (final)**: T6 (after all others)

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development uses testing/development databases via Doppler-managed `DATABASE_URL`.
- **Shared resource isolation**: Integration/e2e tests run under `doppler run --` which injects the test-database credentials. The new `create_tables()` extension uses `IF NOT EXISTS` semantics — it cannot corrupt existing tables. The detailed-word table (`word_details_nl_ru`) is brand-new and does not exist in production.
- **SQLite cache isolation**: `DetailedWordCacheService` creates pair-scoped SQLite files in a configurable directory. Tests use `tempfile.mkdtemp()` to avoid collisions with production cache files.

## Definition of Done (DoD)

All items must be true:

- `make check` passes in `packages/extract_word_details/` (unit + integration + e2e)
- `make check` passes in `packages/database/` (unit + integration + e2e, including new detailed-word tests)
- `make check` passes in `packages/database_cache/` (unit + integration + e2e, including new detailed-word cache tests)
- Module isolation: no files outside ALLOWED list were touched
- Public interfaces match all three module specs exactly
- Zero legacy tolerance: no dead code, no superseded paths
- No errors silenced: no empty catch, no blanket try/catch discarding exceptions
- Requirements/architecture docs unchanged
- Production database untouched; all development against testing DB only

## Risks + mitigations

- **Risk**: OQ-1 in extract_word_details spec — exact per-POS field matrix is open.
  - **Mitigation**: Dev must define reasonable field sets based on linguistic needs. The spec says to proceed. Use noun/verb examples from the spec as reference and extend to other POS with appropriate fields (e.g., adjective: comparative/superlative, adverb: usage context, preposition: case governance, etc.).

- **Risk**: All-POS V1 creates a large surface (13 POS types × models + prompts + tests).
  - **Mitigation**: Registry-driven composition. Each POS is a self-contained unit. Enforce per-POS decomposition from the start. Use the 200-line file limit as natural decomposition pressure.

- **Risk**: Schema-version compatibility between `extract_word_details`, `database`, and `database_cache` must be aligned.
  - **Mitigation**: T1 establishes the shared schema registry contract first. T4 and T5 consume it. T6 validates cross-module compatibility.

- **Risk**: Integration/e2e tests require live OpenAI API and live Neon DB.
  - **Mitigation**: These run under `doppler run --` which injects credentials. Unit tests use mocks and do not require external services.

## Sources used

- `packages/extract_word_details/docs/module-spec.md`
- `packages/database/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`
- `packages/core/src/nl_processing/core/models.py`
- `packages/core/src/nl_processing/core/prompts.py`
- `packages/core/src/nl_processing/core/ports.py`
- `packages/core/src/nl_processing/core/exceptions.py`
- `packages/translate_word/` (pattern reference for service, prompts, pyproject.toml, Makefile, tests)
- `packages/database/src/nl_processing/database/` (all source files, backend, tests)
- `packages/database_cache/src/nl_processing/database_cache/` (all source files, tests)
- Root `Makefile`, `pyproject.toml`, `ruff.toml`

## Contract summary

### What (requirements)

- FR-1..FR-11 of `extract_word_details` spec: full extractor implementation
- FR-11..FR-14 of `database` spec: `DetailedWordStore` with CRUD and `create_tables()` extension
- FR-11..FR-15 of `database_cache` spec: `DetailedWordCacheService` with read-through caching

### How (architecture)

- LangChain + OpenAI extraction following `translate_word` pattern
- Registry-driven POS dispatch with per-POS Pydantic models and prompt assets
- Versioned schema serialization shared across extractor, database, and cache
- `AbstractBackend` + `NeonBackend` extension for detailed-word SQL operations
- Pair-scoped SQLite cache with `aiosqlite` for `DetailedWordCacheService`

## Impact inventory (implementation-facing)

- **Module**: `extract_word_details` (`packages/extract_word_details/`) — new package from scratch
- **Module**: `database` (`packages/database/`) — new `DetailedWordStore`, backend methods, SQL queries
- **Module**: `database_cache` (`packages/database_cache/`) — new `DetailedWordCacheService`, local store
- **Interfaces**: `WordDetailsExtractor.extract()`, `DetailedWordStore.get_details()`, `DetailedWordStore.get_or_extract_details()`, `DetailedWordCacheService.get_or_fetch_details()`
- **Data model**: `word_details_nl_ru` table in Neon PostgreSQL, `cached_detailed_words` table in pair-scoped SQLite
- **External services**: OpenAI API (extraction), Neon PostgreSQL (persistence)
- **Test directories**: `packages/extract_word_details/tests/`, `packages/database/tests/`, `packages/database_cache/tests/`
