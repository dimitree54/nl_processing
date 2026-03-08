---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
date: 2026-03-07
author: Dima
parentBrief: docs/planning-artifacts/product-brief.md
---

# Product Brief: database

> For shared project context (technology stack, target users, design principles), see the [shared product brief](../../../docs/product-brief.md).

## Executive Summary

`database` is the remote source-of-truth persistence module for `nl_processing`. It stores the shared multilingual word corpus, per-language translation links, per-user word lists, and per-user exercise progress in Neon PostgreSQL. The module operates directly on the unified `Word` model from `core.models`, so it remains the canonical persistence boundary for the whole pipeline.

The module is intentionally responsible for **correctness, durable persistence, and clean relational structure**, not for ultra-low-latency interactive access. Low-latency reads and local-first progress writes are planned as a separate concern in the new `database_cache` module, which will consume `database` as its remote backend.

Exercise progress is now modeled as **multiple dedicated statistics tables**: one table per language pair and per exercise type. This keeps progress for different exercises isolated, makes table ownership explicit, and gives `database_cache` a clear synchronization contract for each exercise it is initialized with.

### What Makes This Module Special

- **Symmetric language architecture:** each language has its own word table; translation links are stored separately per language pair.
- **Optional fire-and-forget translation:** `add_words()` returns immediately while background translation persists missing target-language entries when a translator dependency is injected.
- **Per-exercise isolation:** statistics are stored in separate tables per exercise type, not mixed in one generic bucket.
- **Remote source of truth:** `database` owns durable state and exposes the snapshot / sync primitives that `database_cache` can build on.
- **Backend abstraction:** the business layer stays separate from the Neon-specific backend implementation.
- **Structured logging:** remote persistence, translation failures, and sync-facing internals are observable without coupling to a specific logging backend.

---

## Core Vision

### Problem Statement

The pipeline needs one authoritative place where words, translations, user vocabulary, and exercise outcomes are stored durably across runs and across devices. Without that layer:

- words are re-added and re-translated unnecessarily;
- user vocabulary is not shared across sessions;
- exercise progress is fragmented or lost;
- downstream modules cannot synchronize against a stable canonical dataset.

### Why `database` Is Still Needed After Introducing `database_cache`

`database_cache` solves a different problem: local latency. It should not become the source of truth. The project still needs a durable remote store that:

- survives device loss and process restarts;
- merges data from multiple sessions and clients;
- owns the shared corpus and translation links;
- provides authoritative exercise statistics per user and per exercise.

### Proposed Solution

An async Python module that:

- provides `DatabaseService` for adding words and reading translated word pairs from PostgreSQL;
- stores per-user progress in **separate score tables per exercise type** for each language pair;
- exposes an internal `ExerciseProgressStore` configured with the exercise types relevant to the caller;
- remains the only module that writes authoritative remote state;
- exposes internal snapshot-export and idempotent score-apply primitives for the planned `database_cache` module;
- uses environment-variable configuration only and fails fast when `DATABASE_URL` is missing.

---

## Success Metrics

### Acceptance Criteria

1. **Correctness:** words are deduplicated, translation links are valid, and per-user word lists stay consistent with the shared corpus.
2. **Exercise isolation:** each configured exercise type persists into its own dedicated statistics table for the selected language pair.
3. **Async translation:** `add_words()` returns immediately; translation persistence continues in the background.
4. **Cache readiness:** the module exposes enough internal remote APIs for `database_cache` to refresh snapshots and replay per-exercise increments safely.

### Readiness Criteria

- `create_tables()` creates corpus, translation, user-word, and per-exercise score tables.
- `ExerciseProgressStore` is explicitly aware of the exercise set it manages.
- Snapshot export and idempotent delta-apply interfaces are specified for `database_cache`.
- Integration and e2e tests pass against a real Neon database.

---

## Scope

This module has no phased MVP. It is the canonical remote persistence layer.

### Core Features

1. **`DatabaseService`** with `user_id`, language-pair configuration, and async public methods.
2. **Per-language word tables** storing `Word.normalized_form` and `Word.word_type`.
3. **Per-language-pair translation link tables** connecting source and target words.
4. **Per-user word lists** referencing the shared corpus.
5. **`add_words(words)`** with deduplication, user association, and async translation.
6. **`get_words(...)`** returning translated `WordPair` items for the current user.
7. **`create_tables()`** and test-only reset/drop helpers.
8. **Per-exercise score tables** per language pair and exercise type.
9. **`ExerciseProgressStore`** configured with a set of exercise types at initialization.
10. **Snapshot export + idempotent delta apply** as internal support APIs for `database_cache`.
11. **Structured logging** and backend abstraction.

### Module-Specific Dependencies

- `asyncpg` — async PostgreSQL driver for Neon
- translation orchestration is optional and injected by the caller

### Out of Scope

- Local low-latency caching
- Local-first offline progress writes
- Distributed cache invalidation
- User authentication / registration
- Admin UI or schema migration tooling

### Future Vision

- Additional languages and language pairs
- Incremental snapshot export for cache refreshes
- Richer exercise analytics beyond integer balance
- Remote compaction / archival for idempotent score event logs
