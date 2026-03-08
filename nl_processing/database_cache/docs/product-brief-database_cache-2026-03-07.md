---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - nl_processing/database/docs/product-brief-database-2026-03-02.md
  - nl_processing/database/docs/prd_database.md
  - nl_processing/database/docs/architecture_database.md
  - nl_processing/sampling/docs/product-brief-sampling-2026-03-04.md
date: 2026-03-07
author: Dima
parentBrief: docs/planning-artifacts/product-brief.md
---

# Product Brief: database_cache

> For shared project context (technology stack, target users, design principles), see the [shared product brief](../../../docs/planning-artifacts/product-brief.md).

## Executive Summary

`database_cache` is a new local-first acceleration module for the vocabulary practice loop. It sits in front of the remote `database` module and keeps a durable local snapshot of one user's translated words and exercise statistics. Its goal is to make hot-path operations such as word retrieval, score-aware reads for sampling, and writing exercise outcomes complete in under 200ms without waiting for Neon.

The module initializes with a specific language pair, a cache TTL, and an explicit list of exercise types. If the local snapshot is older than the configured TTL, the module immediately serves the existing snapshot and starts a background refresh. If the caller records an exercise outcome, the score is updated locally at once and pushed to the remote `database` module later through a durable outbox.

### What Makes This Module Special

- **Local-first practice loop:** hot-path reads and score writes never depend on remote round-trips.
- **Stale-while-revalidate:** stale data can still be served while refresh happens asynchronously.
- **Durable local state:** cache data survives process restarts because it is stored in a local embedded database.
- **Exercise-aware initialization:** the cache instance is initialized with the concrete exercise set it must support.
- **Auto-flush on write:** every exercise result triggers an automatic background flush to the remote database — no manual sync calls needed.
- **Offline-safe sync model:** if the remote database is unreachable, local writes are still acknowledged immediately and retried later.

---

## Core Vision

### Problem Statement

Remote database access is too slow for the interactive practice loop. The application needs to:

- fetch user words quickly;
- read score-aware candidate sets for sampling;
- record whether the user answered correctly;
- continue working even when the remote database is slow or temporarily unavailable.

Doing all of that directly against Neon risks user-visible latency far above the desired sub-200ms experience.

### Why Existing Solutions Fall Short

- **Direct `database` reads:** correct but network-bound.
- **Pure in-memory caches:** not persistent, not TTL-based, not exercise-aware, and not safe for offline replay.
- **In-memory-only caches:** lose data on restart and cannot safely queue score deltas.

### Proposed Solution

An async Python module that:

- stores a durable local snapshot of translated `WordPair` items and per-exercise scores;
- initializes with `user_id`, language pair, cache TTL, and `exercise_types`;
- serves reads entirely from local storage;
- updates local exercise scores immediately, appends a sync event to a durable outbox, and automatically starts a background flush to the remote database;
- refreshes stale snapshots in the background without blocking reads;
- retries failed flush attempts on the next write, ensuring eventual delivery using idempotent event IDs.

---

## Success Metrics

### Acceptance Criteria

1. **Warm-cache latency:** `get_words()`, `get_word_pairs_with_scores()`, and `record_exercise_result()` complete in under 200ms on a warm local cache.
2. **Immediate local consistency:** after recording an answer, subsequent local reads reflect the updated score immediately.
3. **Stale startup behavior:** if a snapshot exists but is stale, initialization does not wait for a remote refresh.
4. **Sync safety:** acknowledged local score writes are neither lost nor double-applied remotely across retries and restarts.

### Readiness Criteria

- local cache survives process restart;
- TTL-based background refresh is implemented in the design;
- the configured exercise set is part of class initialization;
- the refresh and flush protocols are defined against `database`.

---

## Scope

This module exists specifically to accelerate the hot practice path.

### Core Features

1. **`DatabaseCacheService`** configured with user, language pair, exercise set, and cache TTL
2. **Durable local snapshot** of translated word pairs
3. **Local score cache** for all configured exercise types
4. **Immediate local score writes** with offline outbox persistence
5. **Background refresh** when the cache is stale
6. **Automatic background flush** of pending score deltas after every write (fire-and-forget)
7. **Status reporting** for readiness, staleness, and pending sync volume
8. **Low-latency read APIs** consumed by `sampling`

### Module-Specific Dependencies

- `database` — remote source of truth and sync target
- local embedded SQL database (SQLite via aiosqlite)

### Out of Scope

- Owning the shared remote corpus
- Translating new words
- Replacing `sampling`
- Distributed multi-device cache coherence beyond eventual remote sync

### Future Vision

- Incremental snapshot refresh instead of full refresh
- Optional in-memory hot index on top of the local SQL store
- Support for caching newly added words immediately after `database.add_words()`
