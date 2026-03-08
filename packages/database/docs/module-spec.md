---
title: "database Module Spec"
module_name: "database"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
---

# Module Spec: database

## 1. Module Snapshot

### Summary

`database` is the authoritative remote persistence layer for `nl_processing`. It stores the shared corpus of words, translation links, per-user vocabulary membership, and per-user exercise progress in Neon PostgreSQL. The module is optimized for correctness and durable state, not hot-path local latency; cache and offline concerns are intentionally delegated to `database_cache`. It also provides the default remote implementation for the shared score-provider and cache-sync ports defined in `core`.

### System Context

The module sits below the LLM-facing extract/translate modules and above downstream practice/caching flows. It exposes `DatabaseService` as the main public persistence API and `ExerciseProgressStore` as the default remote implementation behind the shared score-provider and cache-sync contracts used by consumers such as `sampling` and `database_cache`.

### In Scope

- `DatabaseService` for adding words, reading translated word pairs, and creating tables.
- Canonical remote persistence of words, translation links, and user-word membership.
- Per-exercise score tables, remote snapshot export, and idempotent score-delta replay.
- Backend abstraction, structured logging, and test-only reset helpers.

### Out of Scope

- Local caching, offline writes, or stale-while-revalidate behavior.
- User authentication or user management.
- Admin UIs, dashboards, or migration tooling outside table creation.
- Interactive latency optimization beyond reasonable remote efficiency.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Neon PostgreSQL remains the default remote backend for production and integration testing. | Needs Review | Current concrete backend is `NeonBackend` over `asyncpg`. |
| A-2 | The current production workflow remains focused on the NL/RU language pair even though parts of the schema are structured symmetrically. | Needs Review | Some helpers still hardcode `nl`/`ru` defaults and table creation paths. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `DatabaseService(user_id, source_language, target_language, backend?, translator?)` with async `add_words()`, `get_words()`, and `create_tables()` methods. | Must | Main public API surface. |
| FR-2 | `add_words()` must deduplicate words by normalized form within a language, associate them with the current user, and return `AddWordsResult(new_words, existing_words)`. | Must | Dedup is form-based, not type-based. |
| FR-3 | `get_words()` must return only translated `WordPair` items for the configured user and language pair, with optional `word_type`, `limit`, and `random` filters. | Must | Untranslated words stay hidden from read results. |
| FR-4 | `ExerciseProgressStore` must require a non-empty configured `exercise_types` list and expose score-aware reads plus idempotent delta replay. | Must | Default implementation of the shared `core.ports.ScoredPairProvider` and `core.ports.RemoteProgressSyncPort` contracts. |
| FR-5 | `create_tables()` must create the required corpus, translation, user, score, and applied-events tables idempotently. | Must | Remote schema bootstrap entrypoint. |
| FR-6 | Missing `DATABASE_URL` must raise `ConfigurationError`, and remote operation failures must surface as `DatabaseError` or backend failures. | Must | Fail-fast configuration contract. |

### Rules and Invariants

- BR-1: `database` remains the canonical remote source of truth; local cache concerns stay outside this module.
- BR-2: Word deduplication is by `normalized_form` within a language table; `word_type` does not create a second canonical word row.
- BR-3: `delta` values for exercise score updates are limited to `+1` or `-1`.
- BR-4: Read APIs return only completed translation pairs; untranslated source words do not appear in `get_words()`.
- BR-5: Cache-facing snapshot export must return stable remote IDs for both source and target words.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Reliability | Durable correctness is more important than sub-200ms latency. | Remote correctness first | Cache handles the interactive latency problem. |
| NFR-2 | Async | Public and cache-facing operations remain async. | Async-first API | Supports remote I/O without blocking callers. |
| NFR-3 | Retry Safety | Idempotent score replay must be safe across retries. | Atomic apply using event IDs | Important for `database_cache` sync. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | `DATABASE_URL` is missing. | Raise `ConfigurationError` immediately. | Provide valid Doppler/env configuration before use. |
| FM-2 | Remote DB/network/query fails. | Surface backend failure as a database-layer error. | Caller retries or surfaces the issue. |
| FM-3 | Background translation fails after `add_words()`. | Log the failure without undoing the successful write path. | Retry via later workflows if needed. |
| FM-4 | Unknown `exercise_type` or invalid `delta` is passed. | Raise `ValueError` before remote mutation. | Caller fixes the input contract. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Remote persistence schema and canonical word/translation/progress tables.
- Public persistence APIs plus cache-facing snapshot/replay primitives.
- Backend abstraction and structured logging.

**Does Not Own:**

- Local caching, TTL management, or outbox durability.
- Translator construction; translation is injected if desired.
- User-facing practice selection logic.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `DatabaseService.add_words()`, `get_words()`, `create_tables()` | Main public persistence surface. |
| IF-2 | Python API | Inbound | `sampling`, `database_cache` | `ExerciseProgressStore.get_word_pairs_with_scores()`, `export_remote_snapshot()`, `apply_score_delta(...)` | Default implementation of the shared `core.ports` score-provider and remote-sync contracts; snapshot export returns stable source and target IDs for cache rebuilds. |
| IF-3 | External system | Outbound | Neon PostgreSQL via `asyncpg` | SQL tables for words, translations, user membership, scores, and applied events | Default backend implementation. |
| IF-4 | Optional dependency | Inbound | Translator implementation | `translate(words: list[Word]) -> list[Word]` protocol | Injected into `DatabaseService` when auto-translation is wanted. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| `words_<lang>` tables | Owned | Canonical per-language word rows. | Durable remote state | Shared corpus. |
| `translations_<src>_<tgt>` tables | Owned | Translation links between source and target words. | Durable remote state | One table per language pair. |
| `user_words` data | Owned | User membership in the shared corpus. | Durable remote state | Separates shared corpus from per-user vocabulary. |
| `user_word_exercise_scores_<src>_<tgt>_<exercise>` tables | Owned | Per-user progress per exercise type. | Durable remote state | Score tables are exercise-specific. |
| `applied_events_<src>_<tgt>` tables | Owned | Idempotency records for replayed score events. | Durable remote state | Shared across exercise types in one pair. |

### Processing Flow

1. `create_tables()` bootstraps the remote schema for the configured languages, pairs, and exercise slugs.
2. `add_words()` inserts or reuses canonical word rows, associates them with the current user, and optionally schedules background translation for new source words.
3. `get_words()` reads translated pairs for the user and reconstructs them into shared `WordPair` objects.
4. `ExerciseProgressStore` overlays per-exercise score data onto translated pairs, serves `sampling` through scored reads, and serves `database_cache` through snapshot export plus idempotent score-delta replay.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep `database` as the canonical remote source of truth. | Decided | Prevents cache layers from owning durability semantics. | Cache features build on top of explicit sync primitives. |
| DEC-2 | Separate schema by language, language pair, and exercise type. | Decided | Keeps data ownership explicit and progress isolated per exercise. | Table creation and naming must stay coordinated. |
| DEC-3 | Inject the translator instead of constructing `translate_word` internally. | Decided | Preserves package independence and explicit composition. | Callers opt into automatic translation explicitly. |
| DEC-4 | Use applied-event idempotency plus one atomic replay operation for score deltas. | Decided | Supports safe retries from cache flush workflows. | Event IDs must stay unique within a language-pair scope. |
| DEC-5 | Expose cross-package sync behavior through shared `core` contracts rather than concrete cache-specific types. | Decided | Keeps `database` as the default implementation without forcing consumers to type against one concrete class. | Snapshot/export behavior must stay aligned with the shared DTOs and ports in `core`. |

### Consistency Rules

- CR-1: `create_tables(exercise_slugs)` and `ExerciseProgressStore(exercise_types)` must stay aligned on exercise slug naming.
- CR-2: When the module promises multi-language flexibility, helper defaults and schema bootstrap paths must not quietly hardcode only one pair.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, DEC-1, DEC-3 | QA-1 |
| FR-4 | IF-2, DEC-2, DEC-4, DEC-5, CR-1 | QA-2 |
| FR-5 | IF-3, DEC-2 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `DatabaseService` persists canonical words, associates them with users, and returns translated `WordPair` results only when translations exist.
- AC-2: `ExerciseProgressStore` exposes score-aware snapshots with stable remote IDs plus idempotent score replay for configured exercises.
- AC-3: Remote schema bootstrap remains idempotent for the current table set.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest` suites, with integration/e2e tests running against a real Neon database under Doppler-managed configuration.
- Keep remote reset helpers confined to tests.

**Unit:**

- Mock-backend coverage for deduplication, warnings, progress logic, validation, and replay semantics.

**Integration:**

- Real Neon schema creation, CRUD operations, score table behavior, and snapshot/export correctness.

**Contract:**

- Validate idempotent replay and exercise-type validation paths on `ExerciseProgressStore`.

**E2E or UI Workflow:**

- Full flow from adding words to translated reads and persisted score updates.

**Operational or Non-Functional:**

- Manual verification of Doppler/Neon configuration before running integration or e2e suites.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Unit + E2E | Deduplication and add/read flow tests | PR CI / nightly | Covers the main write/read contract. |
| QA-2 | FR-4 | Unit + Integration | Progress-store validation and snapshot/replay tests | PR CI / nightly | Protects sync-facing behavior. |
| QA-3 | FR-5 | Integration | Table-creation idempotency tests | PR CI / nightly | Verifies remote bootstrap behavior. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via package check | Preserve database package quality. | PR CI | Lint or dead-code failures. |
| SC-2 | Package tests | Preserve remote schema and service behavior. | PR CI | Unit/integration/e2e failures. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Neon environment readiness | Live DB tests depend on external credentials and connectivity. | Validate `DATABASE_URL` via Doppler and run a simple connectivity/bootstrap flow before deeper tests. | Successful bootstrap/test output. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Multi-language aspirations and NL/RU-specific helpers drift apart. | Callers may assume broader support than the current helper paths actually provide. | Document current pair reality honestly and revisit when adding the next pair. |
| RISK-2 | Event-id idempotency is scoped per language pair, not per exercise. | Reused event IDs across exercises could collide. | Keep event IDs globally unique per flush event. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should the module formalize itself as NL/RU-only for now, or complete the remaining work needed for true multi-language bootstrap helpers? | Open | Project owner to decide before new pair support is announced | The schema is more flexible than some helper defaults. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending explicit language-support roadmap work | Revisit before adding another pair |

### Deferred Work

- D-1: Tighten real-database coverage around idempotent replay if cache sync becomes more central.
- D-2: Reconcile helper defaults with any future multi-language expansion.
