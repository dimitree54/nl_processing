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
  - nl_processing/database/docs/architecture_database.md
  - nl_processing/sampling/docs/prd_sampling.md
workflowType: 'architecture'
project_name: 'nl_processing'
user_name: 'Dima'
date: '2026-03-07'
scope: 'database_cache'
parentArchitecture: docs/planning-artifacts/architecture.md
---

# Architecture Decision Document — database_cache

> For shared architectural decisions (core package, code style, patterns, project structure), see the [shared architecture](../../../docs/planning-artifacts/architecture.md). This document covers only module-specific decisions.

## Module-Specific Architectural Decisions

### Decision: `database` Remains the Source of Truth

`database_cache` is an acceleration layer, not an authoritative datastore. It mirrors a subset of remote state locally and eventually synchronizes writes back to `database`.

**Implication:** cache rebuild is always possible from remote state; cache corruption is recoverable.

### Decision: Exercise Types Are Declared at Initialization

Each cache instance is initialized with `exercise_types: list[str]`.

**Rationale:**

- remote `database` stores one table per exercise type;
- the cache must know exactly which exercise scores it mirrors;
- `sampling` and exercise flows usually operate on a stable exercise set inside one session / object lifetime.

### Decision: Local Durable Store Is SQLite

The local cache uses a single SQLite file per `(user_id, source_language, target_language)` cache instance.

**Rationale:**

- embedded database, no extra server process;
- durable on local disk;
- fast enough for sub-200ms local reads and writes;
- SQL remains a good fit for filtering, limits, and score joins.

**Operational note:** the cache file should live on a local filesystem, not a network mount.

### Decision: Stale-While-Revalidate Refresh Policy

Freshness is determined by comparing `last_refresh_completed_at` with the configured TTL.

Behavior:

1. If a readable snapshot exists and is fresh: serve it.
2. If a readable snapshot exists and is stale: serve it immediately and start background refresh.
3. If no readable snapshot exists: start bootstrap refresh and mark the cache not ready.

### Decision: Local Snapshot + Local Overlay

The local cache keeps:

- a durable snapshot of translated word pairs downloaded from remote `database`;
- a durable table of local score values;
- a durable outbox of pending score events not yet flushed remotely.

### Decision: Local Writes Use Transactional Outbox Pattern

When the user answers an exercise:

1. local score is updated;
2. a pending score event with unique `event_id` is inserted into the outbox;
3. both changes commit in one local transaction.

**Rationale:** the user gets immediate feedback while the system preserves enough information for later remote replay.

### Decision: Remote Replay Is Idempotent

Each outbox item uses a stable `event_id`. Flush sends that ID to `database.apply_score_delta(event_id, ...)`.

**Rationale:** retries after ambiguous network failures must not double-increment remote scores.

### Decision: Refresh Rebuilds Snapshot Atomically

Refresh writes downloaded data into staging tables and swaps them atomically into the active snapshot.

After the swap, the cache reapplies all still-pending outbox events to the local score state.

**Rationale:** remote refresh must not erase locally acknowledged but not-yet-flushed score updates.

### Decision: `sampling` Reads Through `database_cache`

`sampling` should treat `database_cache.get_word_pairs_with_scores()` as its primary hot-path data source.

**Rationale:** sampling needs low-latency access to both translated pairs and exercise-aware scores.

## Local Data Model

### Table: `cached_word_pairs`

Denormalized translated dictionary rows:

| Column | Type | Notes |
|---|---|---|
| `source_word_id` | INTEGER | remote canonical ID, primary key |
| `source_normalized_form` | TEXT | from remote `database` |
| `source_word_type` | TEXT | `PartOfSpeech.value` |
| `target_word_id` | INTEGER | remote canonical ID |
| `target_normalized_form` | TEXT | translated word |
| `target_word_type` | TEXT | target part of speech |

### Table: `cached_scores`

Normalized local score state:

| Column | Type | Notes |
|---|---|---|
| `source_word_id` | INTEGER | foreign key to cached pair |
| `exercise_type` | TEXT | must belong to configured set |
| `score` | INTEGER | local current value |
| `updated_at` | TEXT | local timestamp |
| | | primary key: `(source_word_id, exercise_type)` |

### Table: `pending_score_events`

Transactional outbox:

| Column | Type | Notes |
|---|---|---|
| `event_id` | TEXT | UUID / idempotency key, primary key |
| `source_word_id` | INTEGER | remote source word ID |
| `exercise_type` | TEXT | configured exercise |
| `delta` | INTEGER | `+1` or `-1` |
| `created_at` | TEXT | local timestamp |
| `flushed_at` | TEXT | nullable |
| `last_error` | TEXT | nullable |

### Table: `cache_metadata`

Single-row or key-value metadata storing:

- configured `exercise_types`
- schema version
- `last_refresh_started_at`
- `last_refresh_completed_at`
- `last_flush_completed_at`
- last background error

## Remote Integration Contract

`database_cache` depends on these remote interfaces from `database`:

```python
class DatabaseCacheSyncBackend(Protocol):
    async def export_user_word_pairs(
        self,
        user_id: str,
        source_language: Language,
        target_language: Language,
    ) -> list[RemoteWordPairRecord]:
        ...

    async def export_user_scores(
        self,
        user_id: str,
        source_language: Language,
        target_language: Language,
        exercise_types: list[str],
    ) -> list[RemoteScoreRecord]:
        ...

    async def apply_score_delta(
        self,
        event_id: str,
        user_id: str,
        source_language: Language,
        target_language: Language,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None:
        ...
```

## Lifecycle Flow

### Initialization

1. Open SQLite file.
2. Ensure local schema exists.
3. Read metadata and validate configured `exercise_types`.
4. Return current `CacheStatus`.
5. If stale or missing, schedule background refresh.

### Refresh

1. Fetch remote word pairs and scores for the configured exercise set.
2. Write them into staging tables.
3. Atomically swap staging into active snapshot.
4. Reapply still-pending local outbox events to `cached_scores`.
5. Update refresh metadata.

### Record Exercise Result

1. Validate `exercise_type`.
2. Update local `cached_scores`.
3. Insert `pending_score_events` row with new `event_id`.
4. Commit transaction.

### Flush

1. Select oldest unflushed events.
2. Replay each event remotely using `event_id`.
3. Mark successful events as flushed locally.
4. Keep failed events pending for retry.

## Module Internal Structure

```
nl_processing/database_cache/
├── __init__.py
├── service.py              # DatabaseCacheService
├── local_store.py          # SQLite schema + local transactions
├── sync.py                 # refresh / flush orchestration
├── models.py               # CacheStatus and internal sync records
├── exceptions.py           # CacheNotReadyError, CacheStorageError, CacheSyncError
├── logging.py
└── docs/
    ├── product-brief-database_cache-2026-03-07.md
    ├── prd_database_cache.md
    └── architecture_database_cache.md
```

## Test Strategy

### Unit Tests

- stale/fresh TTL decisions
- exercise-type validation
- local transaction writes both score and outbox
- `CacheNotReadyError` on true cold start

### Integration Tests

- SQLite local persistence and restart recovery
- refresh rebuild + pending-event overlay
- flush retry behavior with repeated remote failures
- changed `exercise_types` metadata triggers rebuild path

### E2E Tests

- remote snapshot -> local cache -> sampling-facing read
- stale snapshot start does not block user read path
- offline local score write -> later remote flush
- repeated flush of same `event_id` does not double-apply remotely
