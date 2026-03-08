---
title: "database_cache Module Spec"
module_name: "database_cache"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../database/docs/module-spec.md"
---

# Module Spec: database_cache

## 1. Module Snapshot

### Summary

`database_cache` is a durable local-first cache for one user, one language pair, and one configured set of exercise types. It serves practice-path reads from local SQLite, applies score changes locally first, and synchronizes them back to `database` through a background flush path. The module is explicitly an acceleration layer, not the canonical source of truth, and it depends on a shared remote-sync port rather than one hard-coded remote class.

### System Context

The module sits between interactive practice flows and the remote `database` module. It is designed to make warm-cache reads and local score writes fast while still integrating with the remote snapshot/export and idempotent replay contracts owned by `database`. The public constructor supports injection of a compatible remote-sync implementation while preserving `ExerciseProgressStore` as the default adapter, and refresh consumes snapshot payloads that carry both remote word IDs needed for local rebuilds.

### In Scope

- Public `DatabaseCacheService` lifecycle, read, write, refresh, flush, and status APIs.
- Durable local SQLite snapshot of translated pairs and exercise scores.
- Transactional outbox for retry-safe remote replay.
- Background refresh/flush orchestration and status reporting.

### Out of Scope

- Remote source-of-truth ownership.
- Translation or sampling logic itself.
- Distributed cache coordination or multi-device coherence beyond eventual sync.
- External cache servers or in-memory-only cache strategies.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | SQLite remains sufficient as the embedded durable local store for this module. | Needs Review | Current implementation uses one `.db` file per cache instance. |
| A-2 | `database` remains the sole remote sync target and source of truth. | Needs Review | The default remote adapter is `ExerciseProgressStore`, but the public boundary is `core.ports.RemoteProgressSyncPort`. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `DatabaseCacheService(user_id, source_language, target_language, exercise_types, cache_ttl, remote_progress?, local_store?, cache_dir?)`. | Must | Main public API with optional injection hooks for a `core.ports.RemoteProgressSyncPort` and a prebuilt local store. |
| FR-2 | `init()` must open or create the local cache, ensure schema/metadata, and return a `CacheStatus`. | Must | Lifecycle entrypoint. |
| FR-3 | `get_words()` and `get_word_pairs_with_scores()` must read only from local state and must not require a remote round trip on the hot path. | Must | Core acceleration contract. |
| FR-4 | `record_exercise_result()` must validate input, update local score state and outbox state transactionally, and make the change visible to later local reads immediately. | Must | Local-first write path. |
| FR-5 | After a successful local write, the module must trigger background `flush()` automatically while also exposing explicit `refresh()` and `flush()` methods. | Must | Fire-and-forget sync behavior. |
| FR-6 | `refresh()` must rebuild local snapshot state from remote snapshot payloads without losing pending local progress, and `get_status()` must expose readiness/staleness/pending-event metadata. | Must | Cache lifecycle contract. |

### Rules and Invariants

- BR-1: `database` remains the canonical remote source of truth.
- BR-2: `exercise_types` must be non-empty, fixed for a cache instance, and stored in metadata.
- BR-3: Each acknowledged local score write must be visible locally before remote flush completes.
- BR-4: Each pending sync event must carry a unique `event_id` and be replay-safe remotely.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Warm-cache reads and local writes should stay interactive. | Target <200ms | Original module goal. |
| NFR-2 | Availability | Background refresh/flush must not block the hot read path. | No remote wait on warm-path reads | Core reason for the module. |
| NFR-3 | Durability | Acknowledged local changes must survive restarts. | Durable SQLite state + outbox | Needed for offline-safe practice. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Cache is used before init completes successfully. | Raise `CacheNotReadyError` or an equivalent readiness failure. | Call `init()` first and confirm `CacheStatus`. |
| FM-2 | Remote flush fails. | Keep events pending for retry without losing local visibility. | Retry on later flush attempts. |
| FM-3 | Snapshot is stale but present. | Continue serving reads while refresh happens in the background. | Stale-while-revalidate path. |
| FM-4 | Local storage is unavailable or corrupt. | Surface a cache-storage failure and rebuild if possible. | Recreate local cache from remote snapshot when safe. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Local SQLite snapshot, score overlay, outbox, and metadata.
- Read/write APIs for cache-backed practice flows.
- Refresh and flush orchestration plus status reporting.

**Does Not Own:**

- Remote truth, translation, or sampling logic.
- Global cache coordination across devices.
- External cache infrastructure.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `init()`, `get_words()`, `get_word_pairs_with_scores()`, `record_exercise_result()`, `refresh()`, `flush()`, `get_status()` | Main public cache surface. |
| IF-2 | Remote sync | Outbound | `core.ports.RemoteProgressSyncPort` | `export_remote_snapshot() -> list[WordPairSnapshot]` and `apply_score_delta(...)` | Canonical remote contract; default implementation comes from `database.ExerciseProgressStore`. |
| IF-3 | Local storage | Internal | SQLite via `aiosqlite` | Snapshot rows, scores, pending events, metadata | One local DB file per cache instance. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| SQLite cache file | Owned | Durable local store for one `(user, source_language, target_language)` instance. | Persists across restarts | Default location uses temp dir unless overridden. |
| Cached word pairs | Owned | Local snapshot of translated dictionary pairs. | Rebuilt on refresh | Uses remote canonical IDs. |
| Cached scores | Owned | Local score state by `(source_word_id, exercise_type)`. | Updated on writes and refresh overlay | Missing scores read as zero. |
| Pending score events | Owned | Transactional outbox for remote replay. | Retained until successfully flushed | Each row carries `event_id` and error metadata. |
| Cache metadata | Owned | Readiness, freshness, exercise set, and refresh/flush timestamps. | Updated during lifecycle operations | Drives `CacheStatus`. |

### Processing Flow

1. `init()` opens the SQLite file, ensures schema/metadata, inspects freshness, and either serves an existing snapshot or triggers refresh behavior.
2. Read APIs serve word pairs and scored pairs entirely from local storage.
3. `record_exercise_result()` validates `exercise_type` and `delta`, updates local score state plus outbox in one transaction, then returns before background flush completes.
4. `flush()` replays pending events against `database`, and `refresh()` rebuilds local snapshot state before reapplying pending local overlay data.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Use SQLite as the embedded durable store. | Decided | Keeps the cache local, fast, and serverless. | The module inherits SQLite integrity/recovery concerns. |
| DEC-2 | Model the cache as snapshot + normalized local scores + transactional outbox. | Decided | Separates remote state, local overlay, and sync mechanics clearly. | Refresh must reapply pending local changes after snapshot rebuilds. |
| DEC-3 | Use stale-while-revalidate semantics for existing snapshots. | Decided | Avoids blocking practice flows on remote refresh. | Read paths can temporarily serve stale data. |
| DEC-4 | Replay remote writes with stable event IDs. | Decided | Enables safe retries after network or process failures. | Event IDs must remain unique and durable. |
| DEC-5 | Depend on an injected remote-sync port while keeping `ExerciseProgressStore` as the default adapter. | Decided | Reduces concrete coupling without breaking current callers. | Tests and alternate compositions can provide a fake or specialized remote implementation through the public constructor. |

### Consistency Rules

- CR-1: Local writes must never acknowledge state that is not also recorded durably in the outbox transaction.
- CR-2: Refresh must not erase locally acknowledged-but-unflushed progress.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-3 | IF-1, IF-3, DEC-1, DEC-3 | QA-1 |
| FR-4 | IF-1, IF-3, DEC-2, CR-1 | QA-2 |
| FR-6 | IF-2, DEC-2, DEC-4, DEC-5, CR-2 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: Warm-cache reads return local results without waiting on remote calls.
- AC-2: A local score write is visible immediately after acknowledgment and survives process restart.
- AC-3: Failed remote flushes do not lose pending events, and refresh rebuilds local state from stable remote IDs without wiping pending local progress.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest` suites across unit, integration, and e2e layers.
- Keep live remote checks focused on the `database` sync contract while using SQLite locally in tests.

**Unit:**

- Constructor validation, readiness guards, local model reconstruction, local write validation, and auto-flush trigger behavior.

**Integration:**

- SQLite persistence, refresh rebuilds, pending-event overlay, and flush retry behavior.

**Contract:**

- Snapshot export consumption and idempotent replay against the shared remote-sync port, with `ExerciseProgressStore` remaining the default concrete implementation.

**E2E or UI Workflow:**

- Full lifecycle from `init()` through read/write/flush/refresh with a real remote backend.

**Operational or Non-Functional:**

- Validate status reporting and background-job logging in long-running practice scenarios.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-3 | Integration | Local-read and warm-start cache tests | PR CI | Protects hot-path reads. |
| QA-2 | FR-4 | Unit + Integration | Transactional local-write and visibility tests | PR CI | Guards local-first write behavior. |
| QA-3 | FR-6 | Integration + E2E | Refresh/flush replay and pending-overlay tests | PR CI / nightly | Protects sync safety. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via package check | Preserve package quality and packaging. | PR CI | Lint or dead-code failures. |
| SC-2 | Package tests | Preserve cache lifecycle and sync behavior. | PR CI | Unit/integration/e2e failures. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Background error observability | Some background failure/reporting behavior depends on timing and runtime conditions. | Exercise refresh/flush failures and inspect status metadata plus logs. | Logged errors and updated status fields. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Docs and implementation can drift on cold-start semantics (blocking bootstrap vs immediate not-ready state). | Callers may mis-handle initialization behavior. | Keep this spec aligned to the implemented `init()` contract and tests. |
| RISK-2 | Exercise-set drift and metadata rebuild paths are subtle. | Wrong local schema/state could survive across runs. | Keep explicit rebuild tests when exercise-set handling changes. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should `sampling` eventually prefer `database_cache` by default on the hot path instead of reading `database` directly? | Open | Decide when the cache contract is considered stable enough | The current module is designed to support that path. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending practice-path architecture decisions | Revisit when `sampling` integration changes |

### Deferred Work

- D-1: Revisit the default cold-start contract if practice flows need a non-blocking “not ready yet” mode.
- D-2: Decide whether `sampling` should switch to cache-backed reads by default.
