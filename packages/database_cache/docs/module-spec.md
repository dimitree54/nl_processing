---
title: "database_cache Module Spec"
module_name: "database_cache"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../database/docs/module-spec.md"
  - "../../extract_word_details/docs/module-spec.md"
---

# Module Spec: database_cache

## 1. Module Snapshot

### Summary

`database_cache` is a local SQLite cache package for remote data owned by `database`. It owns two acceleration surfaces: `DatabaseCacheService` for user-scoped translated-pair practice data and `DetailedWordCacheService` for pair-scoped rich word-detail records. The module is explicitly an acceleration layer, not the canonical source of truth, and it depends on injected remote interfaces rather than hard-coded remote classes.

### System Context

The module sits between interactive callers and the remote `database` package. `DatabaseCacheService` keeps translated pairs and score updates fast for practice flows, while `DetailedWordCacheService` keeps rich detailed-word reads local after the first remote fetch. Both services must preserve the typed contracts owned upstream by `database` and `extract_word_details`.

### In Scope

- Public `DatabaseCacheService` lifecycle, read, write, refresh, flush, delete, and status APIs.
- Durable local SQLite snapshot of translated pairs and exercise scores.
- Public `DetailedWordCacheService` for pair-scoped detailed-word read-through caching.
- Local full personal-vocabulary reads with `added_at` and per-exercise score stats.
- Transactional outbox for retry-safe score replay.

### Out of Scope

- Remote source-of-truth ownership.
- Translation or detailed-word extraction logic itself.
- Distributed cache coordination or multi-device coherence beyond eventual sync/read-through.
- External cache servers or in-memory-only cache strategies.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | SQLite remains sufficient as the embedded durable store for this package. | Needs Review | Current implementation already uses SQLite. |
| A-2 | `database` remains the sole remote sync target and source of truth. | Needs Review | Both cache surfaces depend on remote contracts owned there. |
| A-3 | V1 local personal-vocabulary reads continue to mirror translated entries only, not untranslated raw membership rows. | Needs Review | Matches the current remote snapshot shape. |
| A-4 | Detailed-word caching should be pair-scoped rather than user-scoped. | Decided | Rich lexical data is shared corpus data, not per-user progress. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `DatabaseCacheService(user_id, source_language, target_language, exercise_types, cache_ttl, remote_progress?, local_store?, cache_dir?)`. | Must | Existing practice-cache API. |
| FR-2 | `DatabaseCacheService.init()` must open or create the local cache, ensure schema/metadata, and return a `CacheStatus`. | Must | Lifecycle entrypoint. |
| FR-3 | `get_words()` and `get_word_pairs_with_scores()` must read only from local state and must not require a remote round trip on the hot path. | Must | Core practice-cache contract. |
| FR-4 | `record_exercise_result()` must validate input, update local score state and outbox state transactionally, and make the change visible to later local reads immediately. | Must | Local-first write path. |
| FR-5 | After a successful local score write, the module must trigger background `flush()` automatically while also exposing explicit `refresh()` and `flush()` methods. | Must | Fire-and-forget sync behavior. |
| FR-6 | `refresh()` must rebuild local snapshot state from remote snapshot payloads without losing pending local progress, and `get_status()` must expose readiness/staleness/pending-event metadata. | Must | Practice-cache lifecycle contract. |
| FR-7 | The module must expose a local personal-vocabulary read API that returns the same translated record shape as remote, including stable IDs, `added_at`, and per-exercise scores. | Must | Hot-path callers should not branch on data source. |
| FR-8 | The module must expose an exercise-progress summary API that reports total translated personal words plus per-exercise negative-word count, ratio, and percentage from local state. | Must | Missing scores count as `0`; negative means `score < 0`. |
| FR-9 | The module must expose delete APIs for one or many source-word IDs that call remote delete first and only then prune local snapshot rows, local scores, and pending score events. | Must | There is no safe local-only delete fallback. |
| FR-10 | `refresh()` must persist the remote `added_at` metadata needed to rebuild the same personal-vocabulary read model locally. | Must | Prevents cache/read parity drift. |
| FR-11 | The module must expose `DetailedWordCacheService(source_language, target_language, remote_store?, local_store?, cache_dir?)`. | Must | New pair-scoped rich-word cache surface. |
| FR-12 | `DetailedWordCacheService` must use a dedicated pair-scoped local SQLite file and dedicated local table(s), separate from user-scoped practice-cache tables. | Must | Rich lexical data is shared across users. |
| FR-13 | `get_or_fetch_details(words)` must return cached detailed-word records for local hits, request remote misses through the injected remote detailed-word store, persist the returned records locally, and return merged typed results in supported-input order. | Must | Read-through cache behavior. |
| FR-14 | Local detailed-word rows must round-trip through the extractor-owned schema registry and must be invalidated if their schema version is incompatible. | Must | Prevents stale or corrupt rich-detail reads. |
| FR-15 | Remote detail-fetch failures must leave the local detailed-word cache unchanged and surface the failure explicitly. | Must | No synthetic fallback data. |

### Rules and Invariants

- BR-1: `database` remains the canonical remote source of truth.
- BR-2: `exercise_types` must be non-empty, fixed for a practice-cache instance, and stored in metadata.
- BR-3: Each acknowledged local score write must be visible locally before remote flush completes.
- BR-4: Each pending sync event must carry a unique `event_id` and be replay-safe remotely.
- BR-5: Local personal-vocabulary reads must match remote ordering and field shape, including `added_at`.
- BR-6: A successful practice-cache delete must also remove pending score events for the deleted source-word IDs.
- BR-7: Detailed-word caching is pair-scoped and user-independent.
- BR-8: Detailed-word cache rows must always round-trip through the shared schema registry and version parser.
- BR-9: Incompatible detailed-word cache rows are invalid and must not be returned to callers.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Warm-cache reads and local writes should stay interactive. | Target <200ms for warm reads | Applies to both cache surfaces. |
| NFR-2 | Availability | Background refresh/flush must not block the hot practice read path. | No remote wait on warm practice reads | Core reason for `DatabaseCacheService`. |
| NFR-3 | Durability | Acknowledged local score changes and cached detail rows must survive restarts. | Durable SQLite state | Needed for offline-safe use. |
| NFR-4 | Schema Safety | Detailed-word cache rows must not bypass typed parsing. | Validate on read and write | Keeps cache aligned with remote schemas. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Practice cache is used before `init()` completes successfully. | Raise `CacheNotReadyError` or equivalent readiness failure. | Call `init()` first and confirm `CacheStatus`. |
| FM-2 | Remote flush fails. | Keep events pending for retry without losing local visibility. | Retry on later flush attempts. |
| FM-3 | Snapshot is stale but present. | Continue serving reads while refresh happens in the background. | Stale-while-revalidate path. |
| FM-4 | Local storage is unavailable or corrupt. | Surface a cache-storage failure and rebuild if possible. | Recreate local cache from remote snapshot when safe. |
| FM-5 | Remote delete fails. | Surface the failure and leave local rows and pending events untouched. | Caller retries after the remote issue is resolved. |
| FM-6 | Remote detailed-word fetch fails on a local miss. | Surface the failure and do not mutate local detailed rows. | Retry later. |
| FM-7 | Local detailed-word row has an incompatible schema version. | Treat the row as invalid, refetch from remote, and fail if the remote payload is also incompatible. | Keeps the cache honest. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Local SQLite practice snapshot, score overlay, outbox, and metadata.
- Local pair-scoped detailed-word cache and read-through orchestration.
- Read/write/delete APIs for cache-backed practice flows.
- Refresh and flush orchestration plus cache status reporting.

**Does Not Own:**

- Remote truth, translation, or detailed-word extraction logic.
- Global cache coordination across devices.
- External cache infrastructure.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `DatabaseCacheService.init()`, `get_words()`, `get_word_pairs_with_scores()`, `list_personal_words()`, `get_progress_summary()`, `record_exercise_result()`, `delete_word()`, `delete_words()`, `refresh()`, `flush()`, `get_status()` | Practice-cache surface. |
| IF-2 | Remote sync | Outbound | Shared remote port backed by `database` | Enriched `export_remote_snapshot()`, `apply_score_delta(...)`, and remote delete calls | Used by practice cache. |
| IF-3 | Python API | Inbound | Callers | `DetailedWordCacheService.get_or_fetch_details(words)` | Pair-scoped detailed-word cache surface. |
| IF-4 | Remote read-through | Outbound | `database.DetailedWordStore` or compatible protocol | `get_details()` / `get_or_extract_details()` for detailed records | Used by detailed-word cache. |
| IF-5 | Local storage | Internal | SQLite via `aiosqlite` | Practice-cache tables, detailed-word cache tables, metadata | Separate DB files per cache surface. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Practice cache file | Owned | Durable local store for one `(user, source_language, target_language)` practice instance. | Persists across restarts | Existing `DatabaseCacheService` scope. |
| Cached word pairs | Owned | Local snapshot of translated pairs plus `added_at` metadata needed for personal-vocabulary reads. | Rebuilt on refresh | Uses remote canonical IDs. |
| Cached scores | Owned | Local score state by `(source_word_id, exercise_type)`. | Updated on writes and refresh overlay | Missing scores read as zero. |
| Pending score events | Owned | Transactional outbox for remote replay. | Retained until successfully flushed | Each row carries `event_id` and error metadata. |
| Detailed-word cache file | Owned | Durable local store for one `(source_language, target_language)` detailed-word cache. | Persists across restarts | Pair-scoped, not user-scoped. |
| Cached detailed rows | Owned | Local copy of remote detailed-word payloads plus schema metadata. | Inserted on fetch and invalidated on mismatch | Parsed through shared registry. |
| Cache metadata | Owned | Readiness, freshness, and schema metadata. | Updated during lifecycle operations | Drives status and invalidation. |

### Processing Flow

1. `DatabaseCacheService.init()` opens the practice-cache SQLite file, ensures schema/metadata, inspects freshness, and either serves an existing snapshot or triggers refresh behavior.
2. Practice read APIs serve word pairs, scored pairs, full personal-vocabulary records, and progress summaries entirely from local practice-cache storage.
3. `record_exercise_result()` validates `exercise_type` and `delta`, updates local score state plus outbox in one transaction, then returns before background flush completes.
4. `delete_word()` and `delete_words()` call the remote delete API first and, on success, prune local rows, scores, and pending events for the deleted IDs.
5. `DetailedWordCacheService.get_or_fetch_details(words)` checks the pair-scoped detailed-word cache first, requests remote misses through the injected detailed-word store, persists validated results locally, and returns merged typed records.
6. Detailed-word reads invalidate incompatible local schema versions and refetch from remote instead of serving stale or unparseable rows.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Use SQLite as the embedded durable store. | Decided | Keeps both cache surfaces local, fast, and serverless. | The package inherits SQLite integrity/recovery concerns. |
| DEC-2 | Model the practice cache as snapshot + normalized local scores + transactional outbox. | Decided | Separates remote state, local overlay, and sync mechanics clearly. | Refresh must reapply pending local changes after snapshot rebuilds. |
| DEC-3 | Use stale-while-revalidate semantics for existing practice snapshots. | Decided | Avoids blocking practice flows on remote refresh. | Read paths can temporarily serve stale data. |
| DEC-4 | Replay remote score writes with stable event IDs. | Decided | Enables safe retries after network or process failures. | Event IDs must remain unique and durable. |
| DEC-5 | Depend on injected remote interfaces while keeping `ExerciseProgressStore` and `DetailedWordStore` as the default adapters. | Decided | Reduces concrete coupling without breaking callers. | Tests can provide fakes or alternates. |
| DEC-6 | Keep practice deletes remote-first instead of building a delete outbox. | Decided | Delete is destructive and the current cache design has no safe eventual-delete mechanism. | Delete availability depends on remote reachability. |
| DEC-7 | Make detailed-word caching pair-scoped and separate from the user-scoped practice cache. | Decided | Rich lexical data is shared corpus data, not per-user progress. | Requires a second local SQLite surface. |
| DEC-8 | Use read-through fetches for detailed-word caching instead of periodic full snapshots. | Decided | Detailed-word access is sparse and content changes infrequently. | Misses pay remote cost once, then stay local. |
| DEC-9 | Invalidate incompatible detailed-word schema versions locally and refetch from remote. | Decided | Keeps the cache aligned with extractor/database schema changes. | Version metadata is required on local rows. |

### Consistency Rules

- CR-1: Local score writes must never acknowledge state that is not also recorded durably in the outbox transaction.
- CR-2: Practice-cache refresh must not erase locally acknowledged-but-unflushed progress.
- CR-3: Practice-cache refresh and local reads must preserve remote `added_at` and record ordering.
- CR-4: Detailed-word cache files and tables must be pair-scoped, not user-scoped.
- CR-5: Detailed-word cache rows must round-trip through the same schema registry and version parser used by the remote store.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-3, FR-4, FR-6 | IF-1, IF-2, DEC-2, DEC-3, DEC-4, CR-1, CR-2 | QA-1 |
| FR-7, FR-8, FR-9, FR-10 | IF-1, IF-2, DEC-6, CR-3 | QA-2 |
| FR-11, FR-12, FR-13 | IF-3, IF-4, IF-5, DEC-7, DEC-8, CR-4 | QA-3 |
| FR-14, FR-15 | IF-3, IF-4, DEC-9, CR-5 | QA-4 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: Warm practice-cache reads return local results without waiting on remote calls.
- AC-2: A local score write is visible immediately after acknowledgment and survives process restart.
- AC-3: Failed remote flushes do not lose pending events, and refresh rebuilds local state from stable remote IDs without wiping pending local progress.
- AC-4: `DetailedWordCacheService` returns cached detailed records for local hits and fetches+presents only misses through the remote detailed-word store.
- AC-5: Incompatible local detailed-word schema rows are invalidated and never served to callers as typed records.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest` suites across unit, integration, and e2e layers.
- Keep live remote checks focused on contracts owned by `database`; keep local behavior SQLite-backed in tests.

**Unit:**

- Constructor validation, readiness guards, local model reconstruction, summary math, delete validation, detail-cache hit/miss behavior, and schema invalidation paths.

**Integration:**

- SQLite persistence, refresh rebuilds with `added_at`, pending-event overlay, delete pruning, detailed-word read-through caching, and schema-version invalidation.

**Contract:**

- Snapshot export consumption, personal-vocabulary cache parity, remote delete behavior, detailed-word round-trips, and remote idempotent replay against the shared remote interfaces.

**E2E or UI Workflow:**

- Full lifecycle from cache init through practice reads/writes and separate detailed-word fetch/reuse flows with a real remote backend.

**Operational or Non-Functional:**

- Validate status reporting and logging for refresh/flush failures, detail-cache misses, and schema invalidations.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-3, FR-4, FR-6 | Unit + Integration | Practice-cache read/write/refresh tests | PR CI | Protects the existing hot-path contract. |
| QA-2 | FR-7, FR-8, FR-9, FR-10 | Integration + E2E | Personal-vocabulary parity, summary, and remote-first delete tests | PR CI / nightly | Protects full-practice read model. |
| QA-3 | FR-11, FR-12, FR-13 | Unit + Integration | Detailed-word cache hit/miss and local persistence tests | PR CI | Covers the new read-through cache surface. |
| QA-4 | FR-14, FR-15 | Unit + Contract | Schema-version invalidation and remote-failure tests | PR CI | Enforces typed cache safety. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks | Preserve package quality and packaging. | PR CI | Lint or dead-code failures. |
| SC-2 | Package tests | Preserve practice-cache and detailed-word cache behavior. | PR CI | Unit/integration/e2e failures. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Background error observability | Some refresh/flush failure behavior depends on timing and runtime conditions. | Exercise refresh/flush failures and detail-cache remote misses, then inspect status metadata plus logs. | Logged errors and updated status fields. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Docs and implementation can drift on cold-start semantics for the practice cache. | Callers may mis-handle initialization behavior. | Keep the spec aligned to the implemented `init()` contract and tests. |
| RISK-2 | Exercise-set drift and metadata rebuild paths are subtle. | Wrong local schema/state could survive across runs. | Keep explicit rebuild tests when exercise-set handling changes. |
| RISK-3 | Detailed-word schema upgrades can invalidate many local rows at once. | The first read after a schema bump may pay a large remote miss cost. | Track schema version explicitly and test invalidation paths. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should pair-scoped detailed-word cache files be garbage-collected automatically when unused, or left as durable local artifacts? | Open | Project owner to decide if local storage pressure becomes a concern | V1 can ship without eviction. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-4 | Approved | Promoted into the cache scope and architecture | FR-11, FR-12, DEC-7 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-2 | OQ-1 | Unresolved | Keep no automatic eviction as the working assumption | Revisit if local storage pressure appears |

### Deferred Work

- D-1: Add automatic eviction for pair-scoped detailed-word cache files if operationally necessary.
- D-2: Revisit whether `sampling` should eventually prefer cache-backed reads by default.
