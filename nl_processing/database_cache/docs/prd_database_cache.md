---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments: ['product-brief-database_cache-2026-03-07.md']
parentPrd: docs/planning-artifacts/prd.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - database_cache

**Author:** Dima
**Date:** 2026-03-07

> For shared requirements (configuration, language support, error handling, NFRs), see the [shared PRD](../../../docs/planning-artifacts/prd.md). This document covers only module-specific requirements.

## Executive Summary

`database_cache` is a local-first cache module that accelerates the practice path for one user and one language pair. It keeps a durable local snapshot of translated words and exercise statistics, serves reads from local storage, and synchronizes with the remote `database` module in the background.

The cache instance is initialized with an explicit `exercise_types` list. This matters because the remote `database` module stores statistics in separate tables per exercise type; the cache must know at initialization time which exercises it mirrors and maintains locally.

The module must support stale-while-revalidate behavior: if the snapshot is old but still present, the user keeps working immediately while a background refresh starts. Progress writes are applied locally first and delivered to the remote database later.

## Success Criteria

### Technical Success

- Warm-cache reads and local score writes stay below 200ms
- Local writes are visible immediately to later reads
- Existing stale snapshots remain usable during background refresh
- Pending local score events survive restarts
- Retried flushes do not double-apply remote score deltas

### Measurable Outcomes

| Metric | Target | Measurement |
|---|---|---|
| Warm-cache read latency | < 200ms | Benchmark on local cache |
| Local score write latency | < 200ms | Benchmark on local cache |
| Stale init blocking time | No remote wait when snapshot exists | Integration test |
| Sync safety | 0 duplicate remote applications per repeated event ID | Integration / e2e test |

## Scope

All features described here are required for the first release of the module.

**Risk Mitigation:**

- **Cold start:** if no snapshot exists, the cache reports not-ready explicitly instead of silently returning misleading empty data.
- **Remote outage:** local score writes remain accepted and queued while remote flush fails.
- **Exercise drift:** exercise types are declared at initialization and stored in metadata; a changed exercise set triggers refresh / local rebuild logic.

## User Journeys

### Journey 1: Warm Start With Stale Cache

Alex starts a study session. A local cache file already exists, but it is older than the configured TTL. `await cache.init()` returns quickly, the old snapshot remains readable, and a background refresh begins without blocking the user.

### Journey 2: Sampling From Local Scores

`sampling` asks for score-aware word pairs. `database_cache` returns translated words plus scores for the configured exercises entirely from local storage, so the sampler can build the next exercise set without waiting for Neon.

### Journey 3: Record an Answer Offline

The user answers incorrectly. Alex calls `record_exercise_result(..., exercise_type="multiple_choice", delta=-1)`. The local score updates immediately and the cache stores a pending sync event. If Neon is unavailable, the session still continues.

### Journey 4: Flush After Connectivity Returns

Connectivity recovers. `database_cache.flush()` replays pending events to `database` using idempotent event IDs. Successfully flushed events are marked complete locally.

## Developer Tool Specific Requirements

### API Surface

**Public interface:**

```python
from datetime import timedelta

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database_cache.service import DatabaseCacheService

cache = DatabaseCacheService(
    user_id="alex",
    source_language=Language.NL,
    target_language=Language.RU,
    exercise_types=["nl_to_ru", "multiple_choice"],
    cache_ttl=timedelta(minutes=30),
    cache_dir="/tmp/my_cache",  # optional; defaults to system temp dir
)

status = await cache.init()
pairs = await cache.get_words(word_type=PartOfSpeech.NOUN, limit=10, random=True)
scored_pairs = await cache.get_word_pairs_with_scores()

await cache.record_exercise_result(
    source_word=Word(normalized_form="fiets", word_type=PartOfSpeech.NOUN, language=Language.NL),
    exercise_type="nl_to_ru",
    delta=-1,
)

await cache.flush()
```

**Status object:**

```python
CacheStatus(
    is_ready=True,
    is_stale=False,
    has_snapshot=True,
    pending_events=3,
    last_refresh_completed_at=...,
    last_flush_completed_at=...,
)
```

**Exceptions:**

- `CacheNotReadyError` — caller asked for cached data before the first usable snapshot existed
- `CacheStorageError` — local database file could not be opened, read, or updated
- `CacheSyncError` — explicit refresh / flush failed and the caller requested the failure synchronously

### Implementation Considerations

- `database_cache` is a downstream consumer of `database`
- `sampling` should prefer `database_cache` as its hot-path source
- `exercise_types` are configured once at initialization and reused throughout the object lifetime
- local storage must be durable, not in-memory only
- local writes must be transactionally coupled to outbox persistence

## Functional Requirements

### Lifecycle

- FR1: Module provides `DatabaseCacheService` in `database_cache/service.py`.
- FR2: Constructor accepts `user_id`, `source_language`, `target_language`, `exercise_types`, `cache_ttl`, and optional local cache path/configuration.
- FR3: `exercise_types` must be non-empty.
- FR4: `init()` opens or creates the local cache and returns a `CacheStatus`.
- FR5: If a local snapshot exists, `init()` must not wait for a remote refresh.
- FR6: If the snapshot is older than `cache_ttl`, `init()` starts a background refresh.
- FR7: If no local snapshot exists, `init()` starts bootstrap refresh and marks the cache as not ready until the first snapshot completes.

### Local Read Path

- FR8: `get_words()` returns translated `WordPair` items from local storage only.
- FR9: `get_words()` supports optional `word_type`, `limit`, and `random` parameters.
- FR10: `get_word_pairs_with_scores()` returns translated word pairs plus scores for all configured exercise types.
- FR11: Missing score values are treated as `0`.
- FR12: Read APIs do not perform remote network calls on the critical path.
- FR13: If no usable snapshot exists yet, read APIs raise `CacheNotReadyError`.

### Local Write Path

- FR14: `record_exercise_result(source_word, exercise_type, delta)` validates that `exercise_type` belongs to the configured set.
- FR15: `delta` is limited to `+1` or `-1`.
- FR16: The local score update and outbox append happen in the same local transaction.
- FR17: After a successful local write, subsequent reads reflect the updated score immediately.
- FR18: Each local write creates a unique `event_id` for remote replay.

### Refresh and Flush

- FR19: `refresh()` fetches translated word pairs and scores for the configured exercise set from `database`.
- FR20: Refresh rebuilds the local snapshot atomically.
- FR21: During refresh, existing readable snapshot data stays available.
- FR22: Pending local outbox events are replayed on top of freshly downloaded scores so unsynced local progress is preserved.
- FR23: `flush()` replays pending events to remote `database`.
- FR24: Failed event flushes remain pending for later retry.
- FR25: Only one refresh job per cache instance may run at a time.
- FR26: Only one flush job per cache instance may run at a time.

### Exercise Set Management

- FR27: The configured exercise set is stored in cache metadata.
- FR28: If `exercise_types` changes between runs, the cache detects the mismatch and triggers local rebuild / refresh logic.
- FR29: The cache may store local scores in a normalized table even though remote `database` uses separate tables per exercise type.

### Status and Observability

- FR30: `get_status()` returns readiness, staleness, pending event count, and last refresh / flush timestamps.
- FR31: Background refresh failures are logged and reflected in status metadata.
- FR32: Background flush failures are logged and reflected in status metadata.

## Non-Functional Requirements (Module-Specific)

### Performance

- NFR1: Warm-cache `get_words()`, `get_word_pairs_with_scores()`, and `record_exercise_result()` should complete in under 200ms.
- NFR2: `init()` with an existing snapshot should not block on remote I/O.
- NFR3: Background refresh and flush must not block read APIs.

### Reliability

- NFR4: Local writes acknowledged to the caller survive process restart.
- NFR5: Retried remote flushes are safe because replay uses idempotent event IDs.
- NFR6: If the local cache file is corrupt, the module surfaces a clear local-storage error and supports rebuild from remote state.

### Consistency

- NFR7: `database` remains the canonical remote source of truth.
- NFR8: The cache may temporarily serve stale data, but pending local score writes must always be visible locally after acknowledgment.
- NFR9: A post-refresh local snapshot must include both the freshly downloaded remote state and all still-pending local events.

### Dependencies

- NFR10: No external cache server is introduced; local persistence uses an embedded local database.
- NFR11: The module depends on `database` for snapshot export and idempotent remote replay.

### Testing

- NFR12: Unit tests verify staleness checks, exercise-set validation, local score overlay, and not-ready behavior.
- NFR13: Integration tests verify refresh / flush behavior against a local embedded database plus mocked remote interfaces.
- NFR14: E2E tests verify a full loop with real `database`: snapshot refresh, sampling-facing reads, offline score write, and later remote flush.
