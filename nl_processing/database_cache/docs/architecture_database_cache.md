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

### Decision: Local Writes Use Transactional Outbox + Auto-Flush

When the user answers an exercise:

1. local score is updated;
2. a pending score event with unique `event_id` is inserted into the outbox;
3. both changes commit in one local transaction;
4. a background flush task is started (fire-and-forget) to push all pending events to the remote database.

The auto-flush is non-blocking: `record_exercise_result()` returns as soon as the local transaction commits (step 3). The background flush (step 4) runs concurrently. If the flush fails (e.g., remote is unreachable), events remain pending and will be retried on the next write's auto-flush.

**Rationale:** the user gets immediate feedback while score deltas are pushed to the remote database as quickly as possible. No manual `flush()` call is needed for normal operation — the system self-synchronizes on every write.

### Decision: Remote Replay Is Idempotent

Each outbox item uses a stable `event_id`. Flush sends that ID to `database.apply_score_delta(event_id, ...)`.

**Rationale:** retries after ambiguous network failures must not double-increment remote scores.

### Decision: Refresh Rebuilds Snapshot Atomically

Refresh deletes existing `cached_word_pairs` and `cached_scores` rows, inserts the freshly downloaded data, reapplies all still-pending outbox events via UPSERT, and commits — all within a single SQLite transaction.

There are no staging tables; atomicity is guaranteed by the enclosing transaction.

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

`database_cache` consumes `ExerciseProgressStore` from the `database` module directly. No separate Protocol is needed because `ExerciseProgressStore` is already a well-defined class with stable instance methods for cache support.

### Snapshot Export

```python
from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database.models import ScoredWordPair

progress = ExerciseProgressStore(
    user_id="alex",
    source_language=Language.NL,
    target_language=Language.RU,
    exercise_types=["nl_to_ru", "multiple_choice"],
)

snapshot: list[ScoredWordPair] = await progress.export_remote_snapshot()
```

`export_remote_snapshot()` returns a list of `ScoredWordPair`, each containing:
- `pair: WordPair` with `source: Word` and `target: Word` (translated pair)
- `scores: dict[str, int]` (score per configured exercise type, missing defaults to 0)
- `source_word_id: int` (remote canonical ID for the source word)

This single call returns word pairs and scores together because they share the same row context.

### Idempotent Score Delta Replay

```python
await progress.apply_score_delta(
    event_id="uuid-here",
    source_word_id=101,
    exercise_type="nl_to_ru",
    delta=-1,  # must be +1 or -1
)
```

- `event_id` is the idempotency key. Repeating the same `event_id` is a no-op.
- `delta` must be +1 or -1 (validated, raises `ValueError` otherwise).
- The check-increment-mark operation is atomic (single database transaction).
- `exercise_type` must belong to the store's configured exercise set.

### Design Decision: Direct Dependency, Not Protocol

`database_cache` depends directly on `ExerciseProgressStore` rather than an abstract Protocol because:
1. There is exactly one implementation of the remote sync contract.
2. The `ExerciseProgressStore` constructor already handles user/language/exercise-type scoping.
3. Test isolation is achieved by injecting a mock backend into the store, not by abstracting the store itself.

## Lifecycle Flow

### Initialization

1. Open SQLite file.
2. Ensure local schema exists.
3. Read metadata and validate configured `exercise_types`.
4. Return current `CacheStatus`.
5. If stale or missing, schedule background refresh.

### Refresh

1. Call `progress.export_remote_snapshot()` to fetch word pairs with scores for the configured exercise set.
2. Within a single transaction: delete existing `cached_word_pairs` and `cached_scores` rows, insert the freshly downloaded word pairs (as tuples) and scores (as a dict keyed by `(source_word_id, exercise_type)`), then reapply still-pending local outbox events to `cached_scores` via UPSERT.
3. Commit the transaction.
4. Update refresh metadata.

### Record Exercise Result

1. Validate `exercise_type`.
2. Update local `cached_scores`.
3. Insert `pending_score_events` row with new `event_id`.
4. Commit transaction.
5. Start background flush (fire-and-forget via `asyncio.create_task`).

### Flush (Auto or Explicit)

Flush runs automatically after every `record_exercise_result()` and is also available as `cache.flush()` for explicit use.

1. If another flush is already running, skip (lock guard).
2. Select oldest unflushed events.
3. Replay each event by calling `progress.apply_score_delta(event_id=..., source_word_id=..., exercise_type=..., delta=...)`.
4. Mark successful events as flushed locally.
5. Keep failed events pending for retry (retried on next auto-flush or explicit call).

## Module Internal Structure

```
nl_processing/database_cache/
├── __init__.py               # empty
├── service.py                # DatabaseCacheService (public class)
├── local_store.py            # SQLite schema + CRUD operations
├── _local_store_queries.py   # DDL and SQL query constants
├── sync.py                   # CacheSyncer: refresh/flush orchestration
├── models.py                 # CacheStatus Pydantic model
├── exceptions.py             # CacheNotReadyError, CacheStorageError, CacheSyncError
├── logging.py                # Module logger helper
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
- `record_exercise_result()` triggers background flush automatically
- auto-flush does not block `record_exercise_result()` return

### Integration Tests

- SQLite local persistence and restart recovery
- refresh rebuild + pending-event overlay
- flush retry behavior with repeated remote failures
- changed `exercise_types` metadata triggers rebuild path
- auto-flush delivers events to remote after `record_exercise_result()`

### E2E Tests

- remote snapshot -> local cache -> sampling-facing read
- stale snapshot start does not block user read path
- `record_exercise_result()` auto-flushes to Neon in background
- repeated flush of same `event_id` does not double-apply remotely
