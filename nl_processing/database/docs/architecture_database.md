---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-07'
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/database/docs/product-brief-database-2026-03-02.md
  - nl_processing/database/docs/prd_database.md
workflowType: 'architecture'
project_name: 'nl_processing'
user_name: 'Dima'
date: '2026-03-07'
scope: 'database'
parentArchitecture: docs/planning-artifacts/architecture.md
---

# Architecture Decision Document — database

> For shared architectural decisions (core package, code style, patterns, project structure), see the [shared architecture](../../../docs/planning-artifacts/architecture.md). This document covers only module-specific decisions.

## Core Data Model: `Word` from `core.models`

The module persists and reconstructs the shared `Word` model from `nl_processing.core.models`:

```python
class Word(BaseModel):
    normalized_form: str
    word_type: PartOfSpeech
    language: Language
```

`language` is inferred from the table being read or written. `word_type` is stored as `PartOfSpeech.value`.

## Module-Specific Architectural Decisions

### Decision: `database` Is the Remote Source of Truth

`database` owns durable remote persistence only. It stores canonical rows and stable IDs in PostgreSQL. Interactive low-latency reads and local-first score writes are explicitly moved to `database_cache`.

**Implication:** `database` must expose clean remote synchronization primitives, but it must not own local cache invalidation, TTL handling, or on-device snapshots.

### Decision: Symmetric Per-Language Word Tables

Each language has its own table (`words_nl`, `words_ru`, ...). No language is globally privileged.

**Rationale:** adding a new language is a table-creation concern, not a schema rewrite.

### Decision: Per-Language-Pair Translation Link Tables

Each language pair has its own translation table (`translations_nl_ru`).

**Rationale:** translation ownership stays explicit at the pair level, and reverse directions can evolve independently.

### Decision: Per-User Word Membership via Junction Table

User vocabulary membership is stored separately from the shared corpus. Shared words live once globally; users only reference them.

### Decision: Separate Score Tables Per Exercise Type

Exercise statistics are stored in one table per language pair **and** per exercise type:

- `user_word_exercise_scores_nl_ru_nl_to_ru`
- `user_word_exercise_scores_nl_ru_multiple_choice`
- `user_word_exercise_scores_nl_ru_listen_and_type`

**Rationale:**

- exercise types are operationally separate concepts;
- table ownership and data volume are easier to reason about;
- `database_cache` can refresh or replay progress for a declared exercise set without mixing unrelated exercise traffic.

### Decision: Exercise Set Is Declared at Store Initialization

`ExerciseProgressStore` is initialized with `exercise_types: list[str]`. The store only manages those exercises.

**Implication:** callers declare their exercise scope once and then reuse the same object for reads / increments inside that scope.

### Decision: Abstract Backend Interface

Business logic stays above an abstract backend. The initial implementation remains `NeonBackend` via `asyncpg`.

**Rationale:** the relational model should stay stable even if the remote PostgreSQL provider changes.

### Decision: Direct Dependency on `translate_word`

`database` directly calls `translate_word.WordTranslator` when new words are added.

**Rationale:** translation is part of the remote persistence flow, not a plugin concern.

### Decision: Cache Support Happens Through Explicit Internal APIs

To support `database_cache`, `database` exposes internal remote-only operations:

```python
class DatabaseCacheSyncBackend(Protocol):
    async def export_user_word_pairs(...) -> list[RemoteWordPairRecord]: ...
    async def export_user_scores(...) -> list[RemoteScoreRecord]: ...
    async def apply_score_delta(event_id: str, ...) -> None: ...
```

**Rationale:** cache refresh and cache flush must depend on explicit remote contracts, not on ad hoc direct SQL from another module.

### Decision: Idempotent Score Replay

`apply_score_delta(event_id, ...)` treats `event_id` as an idempotency key and records that the event was already applied.

**Rationale:** `database_cache` must be able to retry failed or uncertain flushes without double-incrementing remote scores.

### Decision: Structured Logging with Sync Visibility

`database` logs remote translation failures, exercise-table operations, and cache-facing replay/export failures through namespaced loggers.

### Decision: Environment Variable Configuration — Fail Fast

`DATABASE_URL` is required. Missing configuration raises `ConfigurationError`.

## Module Internal Structure

```
nl_processing/database/
├── __init__.py
├── service.py                   # DatabaseService
├── cached_service.py            # legacy prototype helper; superseded by planned database_cache module
├── backend/
│   ├── __init__.py
│   ├── abstract.py
│   └── neon.py
├── models.py                    # AddWordsResult, WordPair, ScoredWordPair
├── exercise_progress.py         # ExerciseProgressStore + cache-support helpers
├── exceptions.py
├── logging.py
├── testing.py
└── docs/
    ├── product-brief-database-2026-03-02.md
    ├── prd_database.md
    └── architecture_database.md
```

## Test Strategy

### Unit Tests

- deduplication and user-word association
- translation fire-and-forget behavior
- per-exercise table selection
- invalid exercise-type validation
- idempotent replay guards

### Integration Tests

- real Neon table creation for multiple exercise tables
- remote export of word pairs and scores
- repeated `event_id` does not double-apply a score delta

### E2E Tests

- add words, translate, read them back
- persist progress independently for several exercises
- exercise snapshot export matches table contents
- replay same idempotency key twice and verify remote score stays unchanged after the first apply
