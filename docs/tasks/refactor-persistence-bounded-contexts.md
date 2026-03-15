---
title: "Execution Task: Refactor Persistence Stack Into Bounded Contexts"
document_type: "task"
modules:
  - "core"
  - "database_core"
  - "database"
  - "database_cache"
  - "sampling"
source_specs:
  - "../module-spec.md"
  - "../../packages/core/docs/module-spec.md"
  - "../../packages/database_core/docs/module-spec.md"
  - "../../packages/database/docs/module-spec.md"
  - "../../packages/database_cache/docs/module-spec.md"
  - "../../packages/sampling/docs/module-spec.md"
---

# Refactor Persistence Stack Into Bounded Contexts

## Objective

Refactor the persistence stack so it stops behaving like a god-module while preserving the current physical PostgreSQL schema, current table families, and current user-visible service entrypoints.

The target state is:

- one physical PostgreSQL database, not several separate databases;
- shared cross-module DTOs and ports owned by `core`;
- `database_core` reduced to a thin storage/provider SPI plus Neon implementation;
- `database` decomposed into bounded-context remote stores and thin public facades;
- `database_cache` reduced to cache/decorator logic over shared ports instead of concrete `database` classes;
- `sampling` kept database-agnostic and focused on weighting and random choice only.

This is a code refactor task, not a docs rewrite task. Existing module specs and repo docs remain the source of truth. Bring code to docs, not docs to code.

## Design Decisions Already Resolved

- Keep one physical Postgres database. Do not split into multiple physical databases or emulate joins in application code.
- Preserve the current table family names and current PK/FK/UNIQUE relationships in this refactor.
- Preserve the current public import paths:
  - `nl_processing.database.DatabaseService`
  - `nl_processing.database.ExerciseProgressStore`
  - `nl_processing.database.DetailedWordStore`
  - `nl_processing.database.TieredExerciseProgressStore`
  - `nl_processing.database_cache.DatabaseCacheService`
  - `nl_processing.database_cache.DetailedWordCacheService`
  - `nl_processing.sampling.WordSampler`
  - `nl_processing.sampling.TieredMultiExerciseSampler`
- Place shared cross-module storage contracts in `core`, not in `database_core`. This follows root repo docs and README.
- Keep `database_core` provider-facing and domain-neutral. It must not own word, translation, personal-vocabulary, detail-record, or exercise-domain operations.
- Keep `database` as the remote source of truth, but split it by bounded context internally.
- Keep `database_cache` as an adapter/decorator layer. It must not own remote truth and must not depend on concrete remote service classes inside its core logic.
- Keep `sampling` independent from the database. It may consume scored/tiered providers via protocols, but it must not know how data is stored or fetched.
- Move tiered repeat-state transition logic into one shared pure implementation used by both remote and cache flows.
- Remove silent fallback behavior from touched code paths. Fail fast on unexpected schema/state mismatches.

## Non-Goals

- No new language-pair support.
- No data migration to new table names.
- No physical database split.
- No migration to another storage engine.
- No docs changes beyond this task file.
- No broad redesign of unrelated extractor/translator packages.

## Required Context

### Docs To Read First

- `README.md`
- `docs/module-spec.md`
- `packages/core/docs/module-spec.md`
- `packages/database_core/docs/module-spec.md`
- `packages/database/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`
- `packages/sampling/docs/module-spec.md`
- `AGENTS.md`

### Existing Code To Read First

#### `core`

- `packages/core/src/nl_processing/core/models.py`
- `packages/core/src/nl_processing/core/protocols.py`
- `packages/core/tests/unit/core/test_protocols.py`

#### `database_core`

- `packages/database_core/src/nl_processing/database_core/backend/abstract.py`
- `packages/database_core/src/nl_processing/database_core/backend/neon.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_detailed.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_delete.py`
- `packages/database_core/src/nl_processing/database_core/backend/_tiered_queries.py`
- `packages/database_core/src/nl_processing/database_core/_database_config.py`

#### `database`

- `packages/database/src/nl_processing/database/__init__.py`
- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- `packages/database/src/nl_processing/database/tiered_progress.py`
- `packages/database/src/nl_processing/database/models.py`
- `packages/database/src/nl_processing/database/detailed_models.py`
- `packages/database/src/nl_processing/database/detailed_ports.py`
- `packages/database/src/nl_processing/database/_translation.py`
- `packages/database/src/nl_processing/database/_tiered_helpers.py`
- `packages/database/src/nl_processing/database/_tiered_backend_ops.py`

#### `database_cache`

- `packages/database_cache/src/nl_processing/database_cache/__init__.py`
- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/ports.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py`

#### `sampling`

- `packages/sampling/src/nl_processing/sampling/service.py`
- `packages/sampling/tests/unit/sampling/test_sampling_weights.py`
- `packages/sampling/tests/unit/sampling/test_tiered_sampler_behavior.py`
- `packages/sampling/tests/unit/sampling/test_tiered_exercise_selection.py`
- `packages/sampling/tests/unit/sampling/test_tiered_protocol_conformance.py`

### Relevant Skills

- `feature-request`
  - Use this as the execution workflow for a large multi-package refactor with staged delivery, validation, and rollout discipline.
- `module-spec-agent`
  - Read this only if implementation reveals a real conflict between code and spec that cannot be resolved inside the current documented contract.
  - Do not update specs in this task unless the user explicitly opens docs scope.

## Current-State Findings That This Task Must Resolve

### 1. `database_core` is not a thin provider layer

`packages/database_core/src/nl_processing/database_core/backend/abstract.py` currently defines one fat `AbstractBackend` that owns domain-shaped methods such as:

- `add_word`
- `get_user_words`
- `increment_user_exercise_score`
- `upsert_word_details`
- `get_word_details_batch`

This keeps domain knowledge in the lowest layer and makes every higher-level concern depend on one large backend contract.

### 2. `database` currently mixes too many responsibilities

The package simultaneously owns:

- public service APIs;
- table bootstrap and backend wiring;
- domain DTO shaping;
- translation/extraction orchestration;
- query batching;
- tiered repeat-state logic.

The main concentration points are:

- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- `packages/database/src/nl_processing/database/tiered_progress.py`

### 3. `database_cache` still depends on concrete `database` code

Current examples:

- `packages/database_cache/src/nl_processing/database_cache/service.py` imports `ExerciseProgressStore`
- the same file lazily imports `DatabaseService`
- `packages/database_cache/src/nl_processing/database_cache/service.py` and `_service_helpers.py` import DTOs from `packages/database/src/nl_processing/database/models.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py` imports `DetailedWordRecord` from `database`

This violates the intended adapter/decorator boundary.

### 4. Shared contract drift already exists

The repo docs say shared cross-module storage contracts belong in `core`, but code is not aligned.

Current inconsistencies:

- `README.md` says shared storage contracts live in `nl_processing.core.ports`, but `packages/core/src/nl_processing/core/ports.py` does not exist.
- `packages/database_cache/src/nl_processing/database_cache/service.py` imports `RemoteProgressSyncPort` from `nl_processing.core.protocols`, but `packages/core/src/nl_processing/core/protocols.py` currently exposes only `ScoredPairProvider`.
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py` imports `nl_processing.core.tiered_models` and `nl_processing.core.tiered_ports`, but those modules do not exist in `packages/core/src/nl_processing/core/`.
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py` imports `nl_processing.database.tiered_exercise_progress`, while the existing module is `packages/database/src/nl_processing/database/tiered_progress.py`.

This drift must be repaired first. The refactor must not build on top of already-broken shared contracts.

### 5. Tiered logic is duplicated and split across the wrong layers

Repeat-state transitions and tiered progress calculations currently exist in more than one place:

- `packages/database/src/nl_processing/database/_tiered_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_result_recorder.py`

This makes cache and remote behavior drift-prone.

### 6. Cache storage still contains silent fallback behavior

`packages/database_cache/src/nl_processing/database_cache/_local_store_base.py` silently swallows `sqlite3.OperationalError` during an `ALTER TABLE` attempt inside `open()`.

That violates the repo rule against hidden errors and fallback-style recovery. This task must replace that behavior with explicit local schema versioning and explicit migration or failure.

### 7. `sampling` separation is incomplete

`packages/sampling/src/nl_processing/sampling/service.py` is already database-agnostic in spirit, but it still contains confusing mixed responsibilities:

- weighting logic and random choice are in the same file;
- tiered exercise-choice logic is hidden inside sampler internals;
- `sample_adversarial()` references `_source_language`, which is not initialized in the current class;
- `TieredMultiExerciseSampler.sample()` is annotated as returning `(str, WordPair)` but actually returns `WordPair`.

This package must be simplified and aligned to its documented contract without giving it new persistence responsibilities.

## Target Architecture

### Layer 1: `core` owns shared cross-module contracts and pure domain helpers

Create a real shared contract surface under `packages/core/src/nl_processing/core/`:

- `ports.py`
  - public re-export surface for cross-module ports
- `progress_ports.py`
  - remote progress sync port
  - scored-pair provider port
  - remote delete port
- `detail_ports.py`
  - detailed-record fetch port
  - translator/extractor ports used across package boundaries
  - payload validator port if still shared
- `tiered_ports.py`
  - tiered candidate provider
  - remote tiered sync port
- `progress_models.py`
  - `PersonalWord`
  - `ExerciseProgressSummary`
  - `EnrichedWordPairSnapshot`
- `detail_models.py`
  - `DetailedWordRecord`
  - `JsonValue`
- `tiered_models.py`
  - `TieredCandidate`
  - `TieredProgressSummary`
  - `TieredSnapshotEntry`
- `repeat_state.py`
  - pure tiered repeat-state transition logic
  - pure tiered progress aggregation logic

Compatibility requirement:

- keep `packages/core/src/nl_processing/core/protocols.py` as a compatibility re-export module if needed;
- keep existing `ScoredPairProvider` import path working.

### Layer 2: `database_core` owns only storage/provider mechanics

`database_core` must stop owning word/progress/detail domain operations.

Target responsibilities:

- database URL/config reading
- async SQL connection lifecycle
- explicit transaction helper(s)
- typed table-name resolution
- schema/bootstrap orchestration for existing table families
- Neon implementation over `asyncpg`
- generic storage exceptions

Target internal structure:

- `connection.py`
- `executor.py`
- `transactions.py`
- `table_names.py`
- `schema.py`
- `backend/neon.py`
- `exceptions.py`

The replacement for the current fat backend contract must be domain-neutral. Domain repositories in `database` should consume low-level execution primitives, not domain verbs exposed by `database_core`.

### Layer 3: `database` owns bounded-context remote implementations

Internally split `packages/database/src/nl_processing/database/` into bounded contexts:

- `lexicon/`
  - canonical words
  - translations
- `user_vocabulary/`
  - personal membership
  - personal-vocabulary reads
  - delete semantics
- `progress/`
  - generic exercise scores
  - remote snapshot export
  - idempotent delta replay
- `details/`
  - detailed-word persistence
  - read-through materialization via extractor port
- `tiered/`
  - repeat-state persistence
  - tiered snapshot export
  - tiered replay

Public classes remain as thin facades:

- `DatabaseService`
- `ExerciseProgressStore`
- `DetailedWordStore`
- `TieredExerciseProgressStore`

They should compose the bounded-context repositories and application services, not contain low-level persistence logic themselves.

### Layer 4: `database_cache` owns local caching and outbox behavior only

Internally split `packages/database_cache/src/nl_processing/database_cache/` into:

- `practice_cache/`
  - local snapshot store
  - score overlay
  - outbox
  - sync orchestrator
- `details_cache/`
  - detailed-record local cache
  - read-through fetch/persist behavior
- `tiered_cache/`
  - tiered snapshot store
  - local repeat-state mirror
  - tiered outbox

The package must depend on shared `core` ports and shared `core` models only. It must not import `database.models`, `database.detailed_models`, or concrete `database` service classes inside core logic.

Default composition is still allowed for backwards compatibility, but it must live in explicit default-builder modules, not inline inside the core cache service classes.

### `sampling` stays algorithmic

Keep `sampling` package-scoped rather than creating a new module.

Split its logic into small files:

- `providers.py`
- `weights.py`
- `tiered_policy.py`
- `random_choice.py`
- `service.py`

Responsibilities:

- provider protocol consumption
- score-to-weight conversion
- tiered exercise selection policy
- RNG-based choice

Non-responsibilities:

- persistence
- query orchestration
- remote/cache wiring

## Physical Schema And Index Invariants

Do not rename, split, or duplicate the current physical table families in this task.

Keep these table families intact:

- `words_<lang>`
- `translations_<src>_<tgt>`
- `user_words`
- `user_word_exercise_scores_<src>_<tgt>_<exercise>`
- `applied_events_<src>_<tgt>`
- `word_details_<src>_<tgt>`
- `user_word_tiered_repeat_state_<src>_<tgt>`

Keep the current PK/FK/UNIQUE relationships intact.

This task is a code-boundary refactor, not a schema redesign. Preserve database-level joins and current stable ids so inter-table access patterns and existing index coverage are not lost.

## Workstreams

### Workstream 0: Repair contract drift before deeper refactoring

- Create `packages/core/src/nl_processing/core/ports.py`.
- Add the missing shared progress/tiered/detail ports and models in `core`.
- Fix the broken/missing import paths in tiered code.
- Add compatibility re-exports so existing imports remain valid while implementations are moved.
- Add protocol conformance tests in `core` for every new shared port.

Do not proceed to deeper decomposition until shared contracts compile cleanly.

### Workstream 1: Move shared DTOs and ports into `core`

Move cross-package DTOs and ports out of `database` and `database_cache` into `core`.

At minimum, move:

- `PersonalWord`
- `ExerciseProgressSummary`
- `EnrichedWordPairSnapshot`
- `DetailedWordRecord`
- `JsonValue`
- tiered models
- remote progress sync port
- remote delete port
- remote detailed-record port
- tiered sync/candidate ports
- translator/extractor ports that cross package boundaries

Requirements:

- `database_cache` must stop importing DTOs from `database`.
- `database` and `database_cache` must both consume the same shared tiered models and shared repeat-state helpers from `core`.
- public import compatibility must be preserved with re-exports where necessary.

### Workstream 2: Replace fat backend contract in `database_core`

- Remove domain-shaped methods from the current `AbstractBackend` contract.
- Replace it with thin execution/transaction/bootstrap abstractions.
- Move domain-specific SQL and row-shaping concerns out of `database_core` and into `database` bounded-context repositories.
- Keep the Neon implementation in `database_core`, but keep it provider-focused.

Required behavior:

- generic transaction blocks must be explicit;
- no application-domain DTO creation in `database_core`;
- schema bootstrap remains idempotent for the unchanged table families.

### Workstream 3: Decompose `database` by bounded context

Implement internal subpackages and extract logic so each context has one reason to change.

Required splits:

- lexicon persistence
- translation link persistence
- personal membership/delete/read model
- generic exercise progress persistence
- detailed-record persistence/materialization
- tiered repeat-state persistence and replay

Move translation/extraction orchestration out of storage repositories and into thin application services inside `database`.

Keep public facades stable:

- `DatabaseService` becomes a thin composition facade
- `ExerciseProgressStore` becomes a thin composition facade
- `DetailedWordStore` becomes a thin composition facade
- `TieredExerciseProgressStore` becomes a thin composition facade

### Workstream 4: Refactor `database_cache` into protocol-based decorators

- Replace imports of concrete `database` classes and `database` DTOs with shared `core` ports and models.
- Move default remote construction into explicit builder modules.
- Keep local storage and sync orchestration as the package’s only real responsibility.
- Replace the silent `ALTER TABLE` path in `_local_store_base.py` with explicit SQLite schema versioning and explicit migration handling.

Required result:

- cache read/write logic no longer knows about concrete remote implementation classes;
- refresh/flush logic stays intact;
- practice, detailed, and tiered cache surfaces stay separate internally.

### Workstream 5: Unify tiered pure logic

- Delete the duplicate tiered transition logic split across `database` and `database_cache`.
- Define one pure repeat-state transition implementation in `core/repeat_state.py`.
- Define one pure tiered progress aggregation implementation in the same shared layer.
- Make both remote and cache paths consume the same implementation.

This is mandatory. Do not keep two copies of the repeat-state state machine after the refactor.

### Workstream 6: Simplify `sampling`

- Extract score weighting and tiered exercise-choice logic into small internal modules.
- Keep sampler public classes thin and aligned with docs.
- Keep `sampling` dependent only on shared provider protocols and shared models from `core`.
- Do not give `sampling` any database wiring responsibilities.

Specific cleanup required:

- fix the incorrect tiered sampler return annotation;
- isolate or remove broken non-contract logic from the supported execution path;
- keep the documented public contract as the only supported one.

### Workstream 7: Preserve compatibility and validate every affected package

- Add compatibility re-exports where required.
- Keep public service class import paths stable.
- Run package-local quality gates for every affected package.
- Do not leave partially migrated import graphs.

## External API And Library References

This task does not introduce new external libraries, but it relies on existing standard and third-party APIs that must be used correctly.

### Python `Protocol` and `@runtime_checkable`

Use `Protocol` for shared cross-package contracts and `@runtime_checkable` only where runtime structural checks are actually needed.

Example:

```python
from typing import Protocol, runtime_checkable

from nl_processing.core.progress_models import EnrichedWordPairSnapshot


@runtime_checkable
class RemoteProgressSyncPort(Protocol):
    async def export_remote_snapshot(self) -> list[EnrichedWordPairSnapshot]: ...

    async def apply_score_delta(
        self,
        *,
        event_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None: ...
```

Notes from official docs:

- runtime-checkable protocols support `isinstance()`/`issubclass()`;
- runtime checks are structural and only verify presence of attributes, not type signatures;
- runtime-checkable `isinstance()` checks can be slow and should not be put on hot paths.

Sources:

- Python typing docs: [https://docs.python.org/3.12/library/typing.html](https://docs.python.org/3.12/library/typing.html)
- Protocol section and `runtime_checkable`: lines 1554-1616 in the official docs page above

### `asyncpg` transactions

Use explicit async transaction blocks for any remote operation that must be atomic, especially:

- score delta + applied-event mark;
- tiered score delta + repeat-state update;
- any future multi-step remote mutation introduced by the decomposition.

Example:

```python
async with connection.transaction():
    await connection.execute(...)
    await connection.execute(...)
```

Official docs note that outside an explicit transaction block, changes are applied immediately.

Sources:

- asyncpg usage docs: [https://magicstack.github.io/asyncpg/current/usage.html](https://magicstack.github.io/asyncpg/current/usage.html)

### `aiosqlite` connection and commit behavior

Keep SQLite operations explicit and atomic.

Example:

```python
import aiosqlite

db = await aiosqlite.connect(path)
db.row_factory = aiosqlite.Row
await db.execute(...)
await db.commit()
```

Use the current repo’s local-store pattern as the implementation reference, but remove silent fallback behavior.

Sources:

- aiosqlite docs: [https://aiosqlite.omnilib.dev/en/latest/index.html](https://aiosqlite.omnilib.dev/en/latest/index.html)
- current repo examples:
  - `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
  - `packages/database_cache/src/nl_processing/database_cache/local_store.py`
  - `packages/database_cache/src/nl_processing/database_cache/_tiered_local_store.py`

## Expected Packages And Files To Change

### `core`

Expected new or heavily changed files:

- `packages/core/src/nl_processing/core/ports.py`
- `packages/core/src/nl_processing/core/progress_ports.py`
- `packages/core/src/nl_processing/core/detail_ports.py`
- `packages/core/src/nl_processing/core/tiered_ports.py`
- `packages/core/src/nl_processing/core/progress_models.py`
- `packages/core/src/nl_processing/core/detail_models.py`
- `packages/core/src/nl_processing/core/tiered_models.py`
- `packages/core/src/nl_processing/core/repeat_state.py`
- `packages/core/src/nl_processing/core/protocols.py`
- `packages/core/src/nl_processing/core/__init__.py`
- `packages/core/tests/unit/core/`

### `database_core`

Expected new or heavily changed files:

- `packages/database_core/src/nl_processing/database_core/backend/abstract.py`
- `packages/database_core/src/nl_processing/database_core/backend/neon.py`
- `packages/database_core/src/nl_processing/database_core/_database_config.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_detailed.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_delete.py`
- `packages/database_core/src/nl_processing/database_core/backend/_tiered_queries.py`
- additional thin SPI modules introduced by this task

### `database`

Expected new or heavily changed areas:

- `packages/database/src/nl_processing/database/__init__.py`
- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- `packages/database/src/nl_processing/database/tiered_progress.py`
- `packages/database/src/nl_processing/database/models.py`
- `packages/database/src/nl_processing/database/detailed_models.py`
- `packages/database/src/nl_processing/database/detailed_ports.py`
- `packages/database/src/nl_processing/database/_translation.py`
- `packages/database/src/nl_processing/database/_tiered_helpers.py`
- `packages/database/src/nl_processing/database/_tiered_backend_ops.py`
- new bounded-context subpackages under `lexicon/`, `user_vocabulary/`, `progress/`, `details/`, `tiered/`

### `database_cache`

Expected new or heavily changed areas:

- `packages/database_cache/src/nl_processing/database_cache/__init__.py`
- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/ports.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py`
- new internal subpackages under `practice_cache/`, `details_cache/`, `tiered_cache/`

### `sampling`

- `packages/sampling/src/nl_processing/sampling/service.py`
- new small modules for weights, tiered policy, and provider wiring
- `packages/sampling/tests/unit/sampling/`

## Acceptance Criteria

- Shared cross-module persistence contracts are owned by `core`, and a public `nl_processing.core.ports` module exists.
- `database_cache` no longer imports DTOs from `database.models` or `database.detailed_models`.
- `database_cache` core logic no longer imports concrete `DatabaseService` or `ExerciseProgressStore` classes.
- `database_core` no longer exposes one fat domain-shaped backend contract with word/progress/detail operations.
- `database` is internally split into bounded contexts, and the existing public service classes become thin composition facades.
- Tiered repeat-state transition logic exists in one shared pure implementation and is used by both remote and cache layers.
- `sampling` remains persistence-agnostic and depends only on shared provider ports and shared models.
- The supported public import paths listed at the top of this task remain valid.
- The physical PostgreSQL schema is preserved:
  - no table family renames
  - no split into multiple databases
  - no join removal into application-side reconstruction
- Touched code paths fail fast on schema/state mismatches; no silent fallback behavior remains in the refactored areas.
- No touched Python file exceeds the repo file-size limit.
- All affected package-local quality gates are green:
  - `packages/core`
  - `packages/database_core`
  - `packages/database`
  - `packages/database_cache`
  - `packages/sampling`

## Verification Plan

### Package-Level Checks

Run all of the following after implementation:

```bash
cd packages/core && make check
cd packages/database_core && make check
cd packages/database && make check
cd packages/database_cache && make check
cd packages/sampling && make check
```

### Mandatory Automated Coverage

#### `core`

- protocol conformance tests for every new shared port
- model round-trip tests for moved shared DTOs
- repeat-state transition matrix tests moved to the shared pure layer

#### `database_core`

- integration tests prove unchanged schema bootstrap and remote connectivity behavior
- transaction-focused tests cover atomic multi-step remote mutations

#### `database`

- existing unit/integration/e2e coverage remains green
- additional tests prove facades still expose the same public behavior after internal decomposition
- tests prove remote snapshot export still matches cache expectations
- tests prove tiered replay still behaves atomically and uses the shared transition logic

#### `database_cache`

- tests prove no behavior regression in refresh/flush/local-write semantics
- tests prove cache services consume shared `core` ports/models rather than `database` DTO internals
- tests prove explicit local schema handling works without silent swallow behavior
- tests prove tiered cache behavior matches the remote tiered transition matrix

#### `sampling`

- tests prove samplers still work with structural providers only
- tests cover extracted weighting helpers and tiered policy helpers
- tests cover the corrected tiered return contract

### Additional Parity Tests Required

- remote tiered transition parity: remote and cache must produce the same next repeat-state for the same input matrix
- snapshot parity: cache rebuild from remote snapshot must preserve ids, `added_at`, scores, and tiered repeat-state
- public import smoke tests: old import paths still work

## Implementation Constraints

- Use `apply_patch` for manual edits.
- Keep touched files below 200 lines by decomposition, not by compacting code.
- Do not introduce fallback branches to preserve legacy behavior. Fix the architecture properly.
- Do not update specs in this task. If implementation reveals a real spec conflict, stop and report it.
- Do not touch unrelated packages.

## Risks And Watchouts

- The refactor spans five packages. Incomplete contract migration will leave circular or half-broken imports.
- The tiered path already has drift. Do not treat tiered as an afterthought inside the generic progress flow.
- Moving DTOs/ports to `core` is the correct architectural boundary, but it expands the implementation scope beyond the original three database packages. This is intentional and required by current repo docs.
- Compatibility re-exports are required during the split. Do not force consumers to update imports in the same change.
- The cache layer currently hides one local schema migration error. Replacing that with explicit versioned handling may expose latent local-state issues, which is correct and expected.

## Blocking Conditions To Surface Immediately

- Stop and report any newly discovered spec contradiction before changing behavior.
- Stop and report any unrelated pre-existing `make check` failure in the affected packages.
- Stop and report if implementation pressure suggests splitting into multiple physical databases. That is explicitly out of scope for this task.
