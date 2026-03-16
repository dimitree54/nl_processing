---
title: "database Module Spec"
module_name: "database"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
  - "../../database_core/docs/module-spec.md"
  - "../../extract_word_details/docs/module-spec.md"
---

# Module Spec: database

> This spec describes the target-state public contract for `database`.
> It defines WHAT the module must provide, not HOW it is implemented.
> Only documented public surfaces in this file are supported.

## 1. Module Snapshot

### Summary

`database` is the authoritative remote persistence layer for `nl_processing`. It owns the public persistence services for canonical words, translation links, pair-specific detailed-word records, per-user vocabulary membership, and per-user exercise scores. Provider mechanics and the default Neon backend live in `database_core`; this module composes that lower layer without expanding the supported public contract with duplicate progress-oriented DTOs or derived read models.

### System Context

The module sits below the LLM-facing extract and translate packages and above downstream practice and cache flows. It exposes `DatabaseService` as the main public persistence API, `DetailedWordStore` as the pair-specific detailed-word persistence surface, and `ExerciseProgressStore` as the default remote score-bearing implementation used by consumers such as `sampling` and `database_cache`. Cache-specific remote contracts remain owned by `database_cache`, even when `database` supplies the default implementation behind them.

### In Scope

- `DatabaseService` for adding words, reading translated word pairs, deleting personal vocabulary entries, and creating tables.
- `DetailedWordStore` for pair-specific detailed-word persistence and get-or-extract behavior.
- `ExerciseProgressStore` for score-aware reads, canonical snapshot export, and idempotent delta replay.
- Public persistence services, supported domain models from `core`, structured logging, and test-only reset helpers.
- Composition over the extracted `database_core` backend/provider layer.

### Out of Scope

- Local caching, offline writes, or stale-while-revalidate behavior.
- Prompt logic, POS-specific extraction rules, or LLM client construction.
- User authentication or user management.
- Admin UIs, dashboards, or migration tooling outside table creation.
- Interactive latency optimization beyond reasonable remote efficiency.
- Tiered mixed-exercise persistence, repeat-state management, tiered snapshot APIs, or dedicated progress-summary/personal-vocabulary DTO families.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Neon PostgreSQL remains the default remote backend for production and integration testing. | Needs Review | Current concrete backend is `NeonBackend` over `asyncpg`. |
| A-2 | The current production workflow remains focused on the NL/RU language pair even though parts of the schema are structured symmetrically. | Needs Review | Some helpers still hardcode `nl`/`ru` defaults and table creation paths. |
| A-3 | Backward compatibility is not required for removing duplicate progress-oriented surfaces from `database`. | Approved | Explicit user direction. |
| A-4 | Detailed-word records are shared corpus data, not per-user data. | Approved | Matches extractor contract. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `DatabaseService(user_id, source_language, target_language, backend?, translator?)` with async `add_words()`, `get_words()`, `delete_word()`, `delete_words()`, and `create_tables()` methods. | Must | Main public API surface. |
| FR-2 | `add_words()` must deduplicate words by normalized form within a language, associate them with the current user, and return `AddWordsResult(new_words, existing_words)`. | Must | Dedup is form-based, not type-based. |
| FR-3 | `get_words()` must return only translated `WordPair` items for the configured user and language pair, with optional `word_type`, `limit`, and `random` filters. | Must | Untranslated words stay hidden from read results. |
| FR-4 | `ExerciseProgressStore` must require a non-empty configured `exercise_types` list and expose only score-bearing reads and sync primitives needed by downstream modules: `increment()`, `get_word_pairs_with_scores()`, `export_remote_snapshot()`, and `apply_score_delta(...)`. | Must | `get_word_pairs_with_scores()` returns shared `core.ScoredWordPair` items without persistence IDs; canonical snapshot export covers stable-ID sync needs. |
| FR-5 | `create_tables()` must create the required corpus, translation, detailed-word, user, score, and applied-events tables idempotently. | Must | Remote schema bootstrap entrypoint. |
| FR-6 | Missing `DATABASE_URL` must raise `ConfigurationError`, and remote operation failures must surface as `DatabaseError` or backend failures. | Must | Fail-fast configuration contract. |
| FR-7 | `ExerciseProgressStore.export_remote_snapshot()` must return canonical `nl_processing.core.models.WordPairSnapshot` records rather than a database-local snapshot DTO. | Must | Stable IDs, score state, and `added_at` belong to the canonical shared snapshot contract. |
| FR-8 | `PersonalWord`, `ExerciseProgressSummary`, and `EnrichedWordPairSnapshot` are not part of the supported target-state public contract of `database`. | Must | Duplicate or derivable progress-oriented DTOs are intentionally removed. |
| FR-9 | The module must expose delete APIs for one or many source-word IDs that remove only the requesting user's membership rows and that user's exercise-score rows. | Must | Canonical corpus rows and translation links remain intact. |
| FR-10 | Cache-facing snapshot export must include `added_at` together with stable IDs and score maps so `database_cache` can rebuild canonical snapshot records locally and callers can derive any needed views from that data. | Must | Prevents remote/cache read-model drift. |
| FR-11 | The module must expose `DetailedWordStore(source_language, target_language, backend?, extractor?, payload_validator?)` with async `get_details()` and `get_or_extract_details()` methods. | Must | Dedicated pair-specific persistence surface for rich lexical records. |
| FR-12 | `DetailedWordStore` must persist pair-specific detailed-word rows keyed by canonical source-word identity and requested `word_type`, with `schema_key`, `schema_version`, and validated JSON payload columns. | Must | Storage must round-trip through the extractor-owned schema registry. |
| FR-13 | `get_or_extract_details(words)` must read persisted detailed rows first, extract only misses through an injected extractor, persist the validated results, and return merged typed records in supported-input order. | Must | Convenience read-through behavior requested by the user. |
| FR-14 | The store must reject missing canonical source words, unsupported schema versions, and invalid payloads instead of silently creating fallback rows. | Must | No silent storage repair or implicit corpus mutation. |

### Rules and Invariants

- BR-1: `database` remains the canonical remote source of truth; local cache concerns stay outside this module.
- BR-2: Word deduplication is by `normalized_form` within a language table; `word_type` does not create a second canonical word row.
- BR-3: `delta` values for exercise score updates are limited to `+1` or `-1`.
- BR-4: Read APIs return only completed translation pairs; untranslated source words do not appear in `get_words()`.
- BR-5: Cache-facing snapshot export must return canonical `core.WordPairSnapshot` records with stable remote IDs for both source and target words.
- BR-6: `added_at` in exported snapshots is sourced from `user_words.added_at`.
- BR-7: Personal-vocabulary deletes remove only per-user state and must not delete shared corpus rows or translation links.
- BR-8: `PersonalWord`, `ExerciseProgressSummary`, and `EnrichedWordPairSnapshot` are unsupported target-state contract surfaces in `database`.
- BR-9: Detailed-word rows are source-target specific and shared across users.
- BR-10: Detailed-word rows must store only schema-validated payloads and must be parseable through the extractor-owned registry.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Reliability | Durable correctness is more important than sub-200ms latency. | Remote correctness first | Cache handles the interactive latency problem. |
| NFR-2 | Async | Public and cache-facing operations remain async. | Async-first API | Supports remote I/O without blocking callers. |
| NFR-3 | Retry Safety | Idempotent score replay must be safe across retries. | Atomic apply using event IDs | Important for `database_cache` sync. |
| NFR-4 | Schema Safety | Detailed-word payloads must never bypass typed validation. | Validate before write and after read | Prevents drift across extractor, DB, and cache. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | `DATABASE_URL` is missing. | Raise `ConfigurationError` immediately. | Provide valid Doppler/env configuration before use. |
| FM-2 | Remote DB/network/query fails. | Surface backend failure as a database-layer error. | Caller retries or surfaces the issue. |
| FM-3 | Background translation fails after `add_words()`. | Log the failure without undoing the successful write path. | Retry via later workflows if needed. |
| FM-4 | Unknown `exercise_type` or invalid `delta` is passed. | Raise `ValueError` before remote mutation. | Caller fixes the input contract. |
| FM-5 | A caller depends on removed `list_personal_words()`, `get_progress_summary()`, or duplicate progress DTOs. | Those surfaces are unsupported in the target-state contract and must not be treated as public API. | Breaking cleanup is intentional. |
| FM-6 | Delete is requested for a source-word ID outside the user's personal vocabulary. | Raise an explicit domain failure instead of silently succeeding. | Caller refreshes IDs or fixes the request. |
| FM-7 | `get_or_extract_details()` is asked for a word that is not present in the canonical corpus. | Raise an explicit database-layer error. | Caller must persist the source word first. |
| FM-8 | Persisted detailed payload does not match the declared schema version or schema key. | Raise an explicit database-layer error and reject the row. | Fix migration or stored data; do not coerce. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Remote persistence schema and canonical word/translation/progress tables.
- Pair-specific detailed-word tables and read-through store behavior.
- Public persistence APIs plus cache-facing snapshot/replay primitives.
- Per-user membership, delete behavior, and score-bearing snapshot export over per-user state.
- Backend abstraction and structured logging.

**Does Not Own:**

- Local caching, TTL management, or outbox durability.
- Translator or detailed-word extractor construction; LLM-backed services are injected.
- User-facing practice selection logic.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `DatabaseService.add_words()`, `get_words()`, `delete_word()`, `delete_words()`, `create_tables()` | Main public persistence surface for add/get/delete/bootstrap workflows. |
| IF-2 | Python API | Inbound | Callers, `database_cache` | `DetailedWordStore.get_details()` and `get_or_extract_details()` | Pair-specific detailed-word persistence surface. |
| IF-3 | Python API | Inbound | `sampling`, `database_cache` | `ExerciseProgressStore.increment()`, `get_word_pairs_with_scores()`, `export_remote_snapshot()`, `apply_score_delta(...)` | Scored reads return shared `core.ScoredWordPair` values; snapshot export returns canonical `core.WordPairSnapshot` records with stable IDs and `added_at` for cache sync and caller-derived views. |
| IF-4 | External system | Outbound | Neon PostgreSQL via `asyncpg` | SQL tables for words, translations, detailed words, user membership, scores, and applied events | Default backend implementation. |
| IF-5 | Optional dependency | Inbound | Translator implementation | `translate(words: list[Word]) -> list[Word]` protocol | Injected into `DatabaseService` when auto-translation is wanted. |
| IF-6 | Optional dependency | Inbound | Detailed extractor implementation | `extract(words: list[Word]) -> list[DetailedWordRecord]` protocol | Injected into `DetailedWordStore` when read-through extraction is wanted. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| `words_<lang>` tables | Owned | Canonical per-language word rows. | Durable remote state | Shared corpus. |
| `translations_<src>_<tgt>` tables | Owned | Translation links between source and target words. | Durable remote state | One table per language pair. |
| `word_details_<src>_<tgt>` tables | Owned | Pair-specific detailed-word rows with schema metadata and JSON payloads. | Durable remote state | Shared across users. |
| `user_words` data | Owned | User membership in the shared corpus, including `added_at`. | Durable remote state | Separates shared corpus from per-user vocabulary. |
| `user_word_exercise_scores_<src>_<tgt>_<exercise>` tables | Owned | Per-user progress per exercise type. | Durable remote state | Score tables are exercise-specific. |
| `applied_events_<src>_<tgt>` tables | Owned | Idempotency records for replayed score events. | Durable remote state | Shared across exercise types in one pair. |

### Processing Flow

1. `create_tables()` bootstraps the remote schema for the configured languages, pairs, exercise slugs, and detailed-word tables.
2. `add_words()` inserts or reuses canonical word rows, associates them with the current user, and optionally schedules background translation for new source words.
3. `get_words()` reads translated pairs for the user and reconstructs them into shared `WordPair` objects.
4. `delete_word()` and `delete_words()` remove only the user's membership and exercise-score rows for the requested source-word IDs.
5. `DetailedWordStore.get_details()` resolves canonical source-word IDs and returns persisted detailed records for the configured pair.
6. `DetailedWordStore.get_or_extract_details()` reads persisted detail rows first, extracts only misses through the injected extractor, validates payloads, persists them, and returns merged typed records.
7. `ExerciseProgressStore` overlays per-exercise score data onto translated pairs, serves `sampling` through scored reads, and serves `database_cache` through canonical `core.WordPairSnapshot` export plus idempotent score-delta replay.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep `database` as the canonical remote source of truth. | Decided | Prevents cache layers from owning durability semantics. | Cache features build on top of explicit sync primitives. |
| DEC-2 | Separate schema by language, language pair, and exercise type. | Decided | Keeps data ownership explicit and progress isolated per exercise. | Table creation and naming must stay coordinated. |
| DEC-3 | Inject the translator instead of constructing `translate_word` internally. | Decided | Preserves package independence and explicit composition. | Callers opt into automatic translation explicitly. |
| DEC-4 | Use applied-event idempotency plus one atomic replay operation for score deltas. | Decided | Supports safe retries from cache flush workflows. | Event IDs must stay unique within a language-pair scope. |
| DEC-5 | Expose canonical snapshot export through shared `core` models rather than database-local duplicate DTOs. | Decided | Keeps `database` aligned with the cleanup in `core` and `database_cache`. | Snapshot/export behavior must stay aligned with `core.WordPairSnapshot`. |
| DEC-6 | Keep personal-vocabulary delete scoped to per-user membership and scores only. | Decided | Shared corpus ownership stays stable and safe for other users. | Deletes do not reclaim canonical word rows or detailed-word rows. |
| DEC-7 | Derived summaries and translated personal-vocabulary views are caller-owned views over canonical snapshot data, not dedicated `database` DTOs. | Decided | Removes overlapping public models and methods that downstream modules can derive themselves. | `list_personal_words()` and `get_progress_summary()` are out of contract. |
| DEC-8 | Detailed-word rows live in pair-specific tables with versioned JSON payloads. | Decided | Supports many POS models without table explosion. | Parser/version compatibility becomes a first-class constraint. |
| DEC-9 | Inject the detailed extractor instead of constructing `extract_word_details` internally. | Decided | Same dependency-injection pattern as the translator. | Callers opt into automatic extraction explicitly. |
| DEC-10 | `get_or_extract_details()` fails if the source word is missing from the canonical corpus. | Decided | Avoids silent corpus mutation and keeps persistence fail-fast. | Callers must persist or resolve words before requesting details. |
| DEC-11 | Keep cache-specific remote contracts owned by `database_cache`, even when `database` provides the default remote implementation behind them. | Decided | Aligns contract ownership with the cache module cleanup. | `database` documents only its supported persistence and score-bearing surfaces. |

### Consistency Rules

- CR-1: `create_tables(exercise_slugs)` and `ExerciseProgressStore(exercise_types)` must stay aligned on exercise slug naming.
- CR-2: When the module promises multi-language flexibility, helper defaults and schema bootstrap paths must not quietly hardcode only one pair.
- CR-3: Exported remote snapshots and cache-side reconstructed snapshots must use the same canonical field set, including `added_at`.
- CR-4: `DetailedWordStore` must round-trip payloads through the same schema registry and version parser defined by `extract_word_details`.
- CR-5: The supported public contract must not branch into duplicate personal-vocabulary or progress-summary DTO families when the same information can be derived from canonical snapshots.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, DEC-1, DEC-3 | QA-1 |
| FR-4, FR-7, FR-8, FR-10 | IF-3, DEC-2, DEC-4, DEC-5, DEC-7, DEC-11, CR-1, CR-3, CR-5 | QA-2 |
| FR-5 | IF-4, DEC-2 | QA-3 |
| FR-9 | IF-1, IF-4, DEC-6 | QA-4 |
| FR-11, FR-12, FR-13, FR-14 | IF-2, IF-6, DEC-8, DEC-9, DEC-10, CR-4 | QA-5 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `DatabaseService` persists canonical words, associates them with users, and returns translated `WordPair` results only when translations exist.
- AC-2: `ExerciseProgressStore` exposes only the supported score-bearing contract: `increment()`, score-aware reads via `core.ScoredWordPair`, canonical `core.WordPairSnapshot` export for cache sync, and idempotent score replay for configured exercises.
- AC-3: Remote schema bootstrap remains idempotent for the current table set, including the new detailed-word table.
- AC-4: The supported `DatabaseService` contract remains limited to add/get/delete/create-table workflows and does not include `list_personal_words()`.
- AC-5: The supported `database` contract does not include `get_progress_summary()` or duplicate progress-oriented DTOs when callers can derive those views from canonical snapshots.
- AC-6: Deleting one or many personal-vocabulary entries removes only per-user membership and scores.
- AC-7: `DetailedWordStore` returns persisted detailed rows when present and extracts+persists only misses when an extractor is injected.
- AC-8: Invalid detailed payloads, missing source words, and unsupported schema versions fail fast instead of being coerced or silently created.
- AC-9: `database_cache` can consume canonical snapshot export plus the typed detailed-word store contract without private SQL knowledge.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest` suites, with integration/e2e tests running against a real Neon database under Doppler-managed configuration.
- Keep remote reset helpers confined to tests.

**Unit:**

- Mock-backend coverage for deduplication, warnings, score/read logic, canonical snapshot export, validation, replay semantics, detailed-word store validation, and injected dependency behavior.

**Integration:**

- Real Neon schema creation, CRUD operations, score table behavior, delete semantics, canonical snapshot export correctness, detailed-word persistence, and get-or-extract behavior.

**Contract:**

- Validate idempotent replay, canonical snapshot export shape, exercise-type validation paths on `ExerciseProgressStore`, and detailed payload schema parsing plus schema-version enforcement through the extractor-owned registry.

**E2E or UI Workflow:**

- Full flow from adding words to translated reads, canonical snapshot export, deletes, and persisted score updates.
- Persist source words, request details twice, and verify the second call reuses durable data instead of re-extracting.

**Operational or Non-Functional:**

- Manual verification of Doppler/Neon configuration before running integration or e2e suites.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Unit + E2E | Deduplication and add/read flow tests | PR CI / nightly | Covers the main write/read contract. |
| QA-2 | FR-4, FR-7, FR-8, FR-10 | Unit + Integration | Progress-store validation and canonical snapshot/replay tests | PR CI / nightly | Protects the supported sync-facing behavior. |
| QA-3 | FR-5 | Integration | Table-creation idempotency tests | PR CI / nightly | Verifies remote bootstrap behavior, including detailed-word table. |
| QA-4 | FR-9 | Integration + E2E | Single-item and bulk delete tests over user membership and scores | PR CI / nightly | Confirms deletes do not remove shared corpus rows. |
| QA-5 | FR-11, FR-12, FR-13, FR-14 | Unit + Integration | Detailed-word persistence and get-or-extract tests | PR CI / nightly | Covers the new storage surface. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package-local `make check` flow | Preserve database package quality. | PR CI | Formatting, lint, dead-code, duplication, or package test failures. |
| SC-2 | Package tests | Preserve remote schema and service behavior. | PR CI | Unit/integration/e2e failures. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Neon environment readiness | Live DB tests depend on external credentials and connectivity. | Validate `DATABASE_URL` via Doppler and run a simple connectivity/bootstrap flow before deeper tests. | Successful bootstrap/test output. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Multi-language aspirations and NL/RU-specific helpers drift apart. | Callers may assume broader support than the current helper paths actually provide. | Document current pair reality honestly and revisit when adding the next pair. |
| RISK-2 | Some downstream callers may still depend on removed `database` convenience methods or duplicate DTOs. | Breaking cleanup may require coordinated follow-up outside this spec. | Treat this spec as the source of truth and migrate callers to canonical snapshot-based views. |
| RISK-3 | Event-id idempotency is scoped per language pair, not per exercise. | Reused event IDs across exercises could collide. | Keep event IDs globally unique per flush event. |
| RISK-4 | Pair-specific detailed schemas multiply storage and migration complexity as new target languages are added. | Operational footprint grows quickly. | Keep pair-specific tables and schema versioning from day one. |
| RISK-5 | The extractor field matrix for some POS is not finalized yet. | Detailed-word rows may drift before the model contract stabilizes. | Finalize the per-POS field matrix before implementation. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should the module formalize itself as NL/RU-only for now, or complete the remaining work needed for true multi-language bootstrap helpers? | Open | Project owner to decide before new pair support is announced | The schema is more flexible than some helper defaults. |
| OQ-2 | Should `word_details_<src>_<tgt>` retain only the current payload per source word, or also preserve historical schema versions? | Open | Project owner to decide before migration planning | V1 can ship with current-row semantics. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |
| RV-3 | A-3 | Approved | Promoted into explicit breaking cleanup of duplicate progress-oriented surfaces | FR-8, DEC-7 |
| RV-4 | A-4 | Approved | Promoted into explicit detailed-word storage rules | FR-12, BR-9, BR-10 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-5 | OQ-1 | Unresolved | Remains open pending explicit language-support roadmap work | Revisit before adding another pair |
| RV-6 | OQ-2 | Unresolved | Keep current-row storage as the working assumption | Revisit during migration planning |

### Deferred Work

- D-1: Tighten real-database coverage around idempotent replay if cache sync becomes more central.
- D-2: Reconcile helper defaults with any future multi-language expansion.
- D-3: Add source-target pairs beyond `nl -> ru`.
- D-4: Add historical version retention for detailed-word rows if migrations or auditability require it.
- D-5: Evaluate moving canonical word identity from `normalized_form`-only to `(normalized_form, word_type)` if homograph correctness requires it.
