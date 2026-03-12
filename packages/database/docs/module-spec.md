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

`database` is the authoritative remote persistence layer for `nl_processing`. It stores the shared corpus of words, translation links, per-user vocabulary membership, and per-user exercise progress in Neon PostgreSQL. The module is optimized for correctness and durable state, not hot-path local latency; cache and offline concerns are intentionally delegated to `database_cache`. It also provides the default remote implementation for the shared score-provider and cache-sync ports defined in `core`, plus the planned remote read/delete surface for a user's personal vocabulary.

### System Context

The module sits below the LLM-facing extract/translate modules and above downstream practice/caching flows. It exposes `DatabaseService` as the main public persistence API and `ExerciseProgressStore` as the default remote implementation behind the shared score-provider and cache-sync contracts used by consumers such as `sampling` and `database_cache`.

### In Scope

- `DatabaseService` for adding words, reading translated word pairs, reading full personal vocabulary entries, deleting personal vocabulary entries, and creating tables.
- Canonical remote persistence of words, translation links, and user-word membership.
- Per-exercise score tables, personal-vocabulary progress summaries, remote snapshot export, and idempotent score-delta replay.
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
| A-3 | V1 personal-vocabulary reads continue to cover translated entries only, not untranslated raw `user_words` rows. | Needs Review | Matches the current join shape and cache snapshot model. |

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
| FR-7 | The module must expose a personal-vocabulary read API that returns translated user entries with stable source and target IDs, `user_words.added_at`, and per-exercise scores. | Must | This is the ergonomic "whole personal database" read surface requested for callers. |
| FR-8 | The module must expose an exercise-progress summary API that reports, for each configured exercise type, total translated personal words plus negative-word count, ratio, and percentage where negative means `score < 0`. | Must | Missing scores count as `0`, not negative. |
| FR-9 | The module must expose delete APIs for one or many source-word IDs that remove only the requesting user's membership rows and that user's exercise-score rows. | Must | Canonical corpus rows and translation links remain intact. |
| FR-10 | Cache-facing snapshot export must include `added_at` together with stable IDs and score maps so `database_cache` can rebuild the same personal-vocabulary read model locally. | Must | Prevents remote/cache read-model drift. |

### Rules and Invariants

- BR-1: `database` remains the canonical remote source of truth; local cache concerns stay outside this module.
- BR-2: Word deduplication is by `normalized_form` within a language table; `word_type` does not create a second canonical word row.
- BR-3: `delta` values for exercise score updates are limited to `+1` or `-1`.
- BR-4: Read APIs return only completed translation pairs; untranslated source words do not appear in `get_words()`.
- BR-5: Cache-facing snapshot export must return stable remote IDs for both source and target words.
- BR-6: Personal-vocabulary `added_at` is sourced from `user_words.added_at`.
- BR-7: Personal-vocabulary deletes remove only per-user state and must not delete shared corpus rows or translation links.

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
| FM-5 | Delete is requested for a source-word ID outside the user's personal vocabulary. | Raise an explicit domain failure instead of silently succeeding. | Caller refreshes IDs or fixes the request. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Remote persistence schema and canonical word/translation/progress tables.
- Public persistence APIs plus cache-facing snapshot/replay primitives.
- Personal-vocabulary read, summary, and delete behavior over per-user state.
- Backend abstraction and structured logging.

**Does Not Own:**

- Local caching, TTL management, or outbox durability.
- Translator construction; translation is injected if desired.
- User-facing practice selection logic.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `DatabaseService.add_words()`, `get_words()`, `list_personal_words()`, `delete_word()`, `delete_words()`, `create_tables()` | Main public persistence surface, including the new personal-vocabulary convenience APIs. |
| IF-2 | Python API | Inbound | `sampling`, `database_cache` | `ExerciseProgressStore.get_word_pairs_with_scores()`, `get_progress_summary()`, `export_remote_snapshot()`, `apply_score_delta(...)` | Default implementation of the shared score-provider and remote-sync contracts; snapshot export now carries the metadata required for cache-side personal-vocabulary reads. |
| IF-3 | External system | Outbound | Neon PostgreSQL via `asyncpg` | SQL tables for words, translations, user membership, scores, and applied events | Default backend implementation. |
| IF-4 | Optional dependency | Inbound | Translator implementation | `translate(words: list[Word]) -> list[Word]` protocol | Injected into `DatabaseService` when auto-translation is wanted. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| `words_<lang>` tables | Owned | Canonical per-language word rows. | Durable remote state | Shared corpus. |
| `translations_<src>_<tgt>` tables | Owned | Translation links between source and target words. | Durable remote state | One table per language pair. |
| `user_words` data | Owned | User membership in the shared corpus, including `added_at`. | Durable remote state | Separates shared corpus from per-user vocabulary. |
| `user_word_exercise_scores_<src>_<tgt>_<exercise>` tables | Owned | Per-user progress per exercise type. | Durable remote state | Score tables are exercise-specific. |
| `applied_events_<src>_<tgt>` tables | Owned | Idempotency records for replayed score events. | Durable remote state | Shared across exercise types in one pair. |

### Processing Flow

1. `create_tables()` bootstraps the remote schema for the configured languages, pairs, and exercise slugs.
2. `add_words()` inserts or reuses canonical word rows, associates them with the current user, and optionally schedules background translation for new source words.
3. `get_words()` reads translated pairs for the user and reconstructs them into shared `WordPair` objects.
4. `list_personal_words()` joins translated user entries with `user_words.added_at` and per-exercise scores, and `get_progress_summary()` derives negative-balance percentages from the same record set.
5. `delete_word()` and `delete_words()` remove only the user's membership and exercise-score rows for the requested source-word IDs.
6. `ExerciseProgressStore` overlays per-exercise score data onto translated pairs, serves `sampling` through scored reads, and serves `database_cache` through enriched snapshot export plus idempotent score-delta replay.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep `database` as the canonical remote source of truth. | Decided | Prevents cache layers from owning durability semantics. | Cache features build on top of explicit sync primitives. |
| DEC-2 | Separate schema by language, language pair, and exercise type. | Decided | Keeps data ownership explicit and progress isolated per exercise. | Table creation and naming must stay coordinated. |
| DEC-3 | Inject the translator instead of constructing `translate_word` internally. | Decided | Preserves package independence and explicit composition. | Callers opt into automatic translation explicitly. |
| DEC-4 | Use applied-event idempotency plus one atomic replay operation for score deltas. | Decided | Supports safe retries from cache flush workflows. | Event IDs must stay unique within a language-pair scope. |
| DEC-5 | Expose cross-package sync behavior through shared `core` contracts rather than concrete cache-specific types. | Decided | Keeps `database` as the default implementation without forcing consumers to type against one concrete class. | Snapshot/export behavior must stay aligned with the shared DTOs and ports in `core`. |
| DEC-6 | Keep personal-vocabulary delete scoped to per-user membership and scores only. | Decided | Shared corpus ownership stays stable and safe for other users. | Deletes do not reclaim canonical word rows. |
| DEC-7 | Define exercise progress explicitly per exercise type as `negative_words / total_words * 100`. | Decided | Score ownership is per exercise table and implicit averaging would hide behavior. | Callers choose how to present one or many exercise summaries. |

### Consistency Rules

- CR-1: `create_tables(exercise_slugs)` and `ExerciseProgressStore(exercise_types)` must stay aligned on exercise slug naming.
- CR-2: When the module promises multi-language flexibility, helper defaults and schema bootstrap paths must not quietly hardcode only one pair.
- CR-3: Personal-vocabulary reads and cache snapshots must use the same ordering and field set, including `added_at`.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, DEC-1, DEC-3 | QA-1 |
| FR-4, FR-8 | IF-2, DEC-2, DEC-4, DEC-5, DEC-7, CR-1 | QA-2 |
| FR-5 | IF-3, DEC-2 | QA-3 |
| FR-7, FR-10 | IF-1, IF-2, DEC-5, CR-3 | QA-4 |
| FR-9 | IF-1, IF-3, DEC-6 | QA-5 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `DatabaseService` persists canonical words, associates them with users, and returns translated `WordPair` results only when translations exist.
- AC-2: `ExerciseProgressStore` exposes score-aware snapshots with stable remote IDs plus idempotent score replay for configured exercises.
- AC-3: Remote schema bootstrap remains idempotent for the current table set.
- AC-4: The module can return the full translated personal vocabulary for a user, including `added_at` and per-exercise scores.
- AC-5: The module can report per-exercise negative-balance percentages over the user's translated personal vocabulary.
- AC-6: Deleting one or many personal-vocabulary entries removes only per-user membership and scores.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest` suites, with integration/e2e tests running against a real Neon database under Doppler-managed configuration.
- Keep remote reset helpers confined to tests.

**Unit:**

- Mock-backend coverage for deduplication, warnings, progress logic, validation, and replay semantics.

**Integration:**

- Real Neon schema creation, CRUD operations, score table behavior, personal-vocabulary joins, delete semantics, and snapshot/export correctness.

**Contract:**

- Validate idempotent replay, personal-vocabulary DTO shape, and exercise-type validation paths on `ExerciseProgressStore`.

**E2E or UI Workflow:**

- Full flow from adding words to translated reads, full personal-vocabulary reads, progress summaries, deletes, and persisted score updates.

**Operational or Non-Functional:**

- Manual verification of Doppler/Neon configuration before running integration or e2e suites.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Unit + E2E | Deduplication and add/read flow tests | PR CI / nightly | Covers the main write/read contract. |
| QA-2 | FR-4 | Unit + Integration | Progress-store validation and snapshot/replay tests | PR CI / nightly | Protects sync-facing behavior. |
| QA-3 | FR-5 | Integration | Table-creation idempotency tests | PR CI / nightly | Verifies remote bootstrap behavior. |
| QA-4 | FR-7, FR-10 | Unit + Integration | Personal-vocabulary read-model and enriched snapshot tests | PR CI / nightly | Covers `added_at`, stable IDs, and per-exercise score maps. |
| QA-5 | FR-9 | Integration + E2E | Single-item and bulk delete tests over user membership and scores | PR CI / nightly | Confirms deletes do not remove shared corpus rows. |

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
| RISK-3 | The requested "whole personal database" may also need untranslated entries, not just translated pairs. | The current join and cache model would be insufficient. | Resolve this before implementation starts. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should the module formalize itself as NL/RU-only for now, or complete the remaining work needed for true multi-language bootstrap helpers? | Open | Project owner to decide before new pair support is announced | The schema is more flexible than some helper defaults. |
| OQ-2 | Does "whole personal database" need untranslated source words, or only translated entries usable in exercises? | Open | Project owner to decide before implementation | Current plan assumes translated entries only. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |
| RV-3 | A-3 | Not yet reviewed | Kept as active assumption | A-3 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending explicit language-support roadmap work | Revisit before adding another pair |
| RV-4 | OQ-2 | Unresolved | Keep translated-entry scope as the working assumption | Resolve before implementation starts |

### Deferred Work

- D-1: Tighten real-database coverage around idempotent replay if cache sync becomes more central.
- D-2: Reconcile helper defaults with any future multi-language expansion.
