---
title: "database Module Spec"
module_name: "database"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
  - "../../extract_word_details/docs/module-spec.md"
---

# Module Spec: database

## 1. Module Snapshot

### Summary

`database` is the authoritative remote persistence layer for `nl_processing`. It stores the shared corpus of words, translation links, pair-specific detailed-word records, per-user vocabulary membership, and per-user exercise progress in Neon PostgreSQL. The module is optimized for correctness and durable state, not hot-path local latency; cache and offline concerns are intentionally delegated to `database_cache`. It also provides the default remote implementation for the shared score-provider and cache-sync ports defined in `core`.

### System Context

The module sits below the LLM-facing extract and translate packages and above downstream practice and cache flows. It exposes `DatabaseService` as the main public persistence API, `DetailedWordStore` as the pair-specific detailed-word persistence surface, and `ExerciseProgressStore` as the default remote implementation behind the shared score-provider and cache-sync contracts used by consumers such as `sampling` and `database_cache`.

### In Scope

- `DatabaseService` for adding words, reading translated word pairs, reading full personal vocabulary entries, deleting personal vocabulary entries, and creating tables.
- `DetailedWordStore` for pair-specific detailed-word persistence and get-or-extract behavior.
- `ExerciseProgressStore` for score-aware reads, summaries, remote snapshots, and idempotent delta replay.
- Remote schema, backend abstraction, structured logging, and test-only reset helpers.

### Out of Scope

- Local caching, offline writes, or stale-while-revalidate behavior.
- Prompt logic, POS-specific extraction rules, or LLM client construction.
- User authentication or user management.
- Admin UIs, dashboards, or migration tooling outside table creation.
- Interactive latency optimization beyond reasonable remote efficiency.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Neon PostgreSQL remains the default remote backend for production and integration testing. | Needs Review | Current concrete backend is `NeonBackend` over `asyncpg`. |
| A-2 | The current production workflow remains focused on the NL/RU language pair even though parts of the schema are structured symmetrically. | Needs Review | Some helpers still hardcode `nl`/`ru` defaults and table creation paths. |
| A-3 | V1 personal-vocabulary reads continue to cover translated entries only, not untranslated raw `user_words` rows. | Needs Review | Matches the current join shape and cache snapshot model. |
| A-4 | Detailed-word records are shared corpus data, not per-user data. | Approved | Matches extractor contract. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `DatabaseService(user_id, source_language, target_language, backend?, translator?)` with async `add_words()`, `get_words()`, `list_personal_words()`, `delete_word()`, `delete_words()`, and `create_tables()` methods. | Must | Main public API surface. |
| FR-2 | `add_words()` must deduplicate words by normalized form within a language, associate them with the current user, and return `AddWordsResult(new_words, existing_words)`. | Must | Dedup is form-based, not type-based. |
| FR-3 | `get_words()` must return only translated `WordPair` items for the configured user and language pair, with optional `word_type`, `limit`, and `random` filters. | Must | Untranslated words stay hidden from read results. |
| FR-4 | `ExerciseProgressStore` must require a non-empty configured `exercise_types` list and expose score-aware reads plus idempotent delta replay. | Must | Default implementation of the shared `core.ports.ScoredPairProvider` and `core.ports.RemoteProgressSyncPort` contracts. |
| FR-5 | `create_tables()` must create the required corpus, translation, detailed-word, user, score, and applied-events tables idempotently. | Must | Remote schema bootstrap entrypoint. |
| FR-6 | Missing `DATABASE_URL` must raise `ConfigurationError`, and remote operation failures must surface as `DatabaseError` or backend failures. | Must | Fail-fast configuration contract. |
| FR-7 | The module must expose a personal-vocabulary read API that returns translated user entries with stable source and target IDs, `user_words.added_at`, and per-exercise scores. | Must | Ergonomic read surface for callers. |
| FR-8 | The module must expose an exercise-progress summary API that reports, for each configured exercise type, total translated personal words plus negative-word count, ratio, and percentage where negative means `score < 0`. | Must | Missing scores count as `0`, not negative. |
| FR-9 | The module must expose delete APIs for one or many source-word IDs that remove only the requesting user's membership rows and that user's exercise-score rows. | Must | Canonical corpus rows and translation links remain intact. |
| FR-10 | Cache-facing snapshot export must include `added_at` together with stable IDs and score maps so `database_cache` can rebuild the same personal-vocabulary read model locally. | Must | Prevents remote/cache read-model drift. |
| FR-11 | The module must expose `DetailedWordStore(source_language, target_language, backend?, extractor?)` with async `get_details()` and `get_or_extract_details()` methods. | Must | Dedicated pair-specific persistence surface for rich lexical records. |
| FR-12 | `DetailedWordStore` must persist pair-specific detailed-word rows keyed by canonical source-word identity and requested `word_type`, with `schema_key`, `schema_version`, and validated JSON payload columns. | Must | Storage must round-trip through the extractor-owned schema registry. |
| FR-13 | `get_or_extract_details(words)` must read persisted detailed rows first, extract only misses through an injected extractor, persist the validated results, and return merged typed records in supported-input order. | Must | Convenience read-through behavior requested by the user. |
| FR-14 | The store must reject missing canonical source words, unsupported schema versions, and invalid payloads instead of silently creating fallback rows. | Must | No silent storage repair or implicit corpus mutation. |

### Rules and Invariants

- BR-1: `database` remains the canonical remote source of truth; local cache concerns stay outside this module.
- BR-2: Word deduplication is by `normalized_form` within a language table; `word_type` does not create a second canonical word row.
- BR-3: `delta` values for exercise score updates are limited to `+1` or `-1`.
- BR-4: Read APIs return only completed translation pairs; untranslated source words do not appear in `get_words()`.
- BR-5: Cache-facing snapshot export must return stable remote IDs for both source and target words.
- BR-6: Personal-vocabulary `added_at` is sourced from `user_words.added_at`.
- BR-7: Personal-vocabulary deletes remove only per-user state and must not delete shared corpus rows or translation links.
- BR-8: Detailed-word rows are source-target specific and shared across users.
- BR-9: Detailed-word rows must store only schema-validated payloads and must be parseable through the extractor-owned registry.

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
| FM-5 | Delete is requested for a source-word ID outside the user's personal vocabulary. | Raise an explicit domain failure instead of silently succeeding. | Caller refreshes IDs or fixes the request. |
| FM-6 | `get_or_extract_details()` is asked for a word that is not present in the canonical corpus. | Raise an explicit database-layer error. | Caller must persist the source word first. |
| FM-7 | Persisted detailed payload does not match the declared schema version or schema key. | Raise an explicit database-layer error and reject the row. | Fix migration or stored data; do not coerce. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Remote persistence schema and canonical word/translation/progress tables.
- Pair-specific detailed-word tables and read-through store behavior.
- Public persistence APIs plus cache-facing snapshot/replay primitives.
- Personal-vocabulary read, summary, and delete behavior over per-user state.
- Backend abstraction and structured logging.

**Does Not Own:**

- Local caching, TTL management, or outbox durability.
- Translator or detailed-word extractor construction; LLM-backed services are injected.
- User-facing practice selection logic.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `DatabaseService.add_words()`, `get_words()`, `list_personal_words()`, `delete_word()`, `delete_words()`, `create_tables()` | Main public persistence surface, including personal-vocabulary convenience APIs. |
| IF-2 | Python API | Inbound | Callers, `database_cache` | `DetailedWordStore.get_details()` and `get_or_extract_details()` | Pair-specific detailed-word persistence surface. |
| IF-3 | Python API | Inbound | `sampling`, `database_cache` | `ExerciseProgressStore.get_word_pairs_with_scores()`, `get_progress_summary()`, `export_remote_snapshot()`, `apply_score_delta(...)` | Default implementation of the shared score-provider and remote-sync contracts; snapshot export carries the metadata required for cache-side personal-vocabulary reads. |
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
4. `list_personal_words()` joins translated user entries with `user_words.added_at` and per-exercise scores, and `get_progress_summary()` derives negative-balance percentages from the same record set.
5. `delete_word()` and `delete_words()` remove only the user's membership and exercise-score rows for the requested source-word IDs.
6. `DetailedWordStore.get_details()` resolves canonical source-word IDs and returns persisted detailed records for the configured pair.
7. `DetailedWordStore.get_or_extract_details()` reads persisted detail rows first, extracts only misses through the injected extractor, validates payloads, persists them, and returns merged typed records.
8. `ExerciseProgressStore` overlays per-exercise score data onto translated pairs, serves `sampling` through scored reads, and serves `database_cache` through enriched snapshot export plus idempotent score-delta replay.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep `database` as the canonical remote source of truth. | Decided | Prevents cache layers from owning durability semantics. | Cache features build on top of explicit sync primitives. |
| DEC-2 | Separate schema by language, language pair, and exercise type. | Decided | Keeps data ownership explicit and progress isolated per exercise. | Table creation and naming must stay coordinated. |
| DEC-3 | Inject the translator instead of constructing `translate_word` internally. | Decided | Preserves package independence and explicit composition. | Callers opt into automatic translation explicitly. |
| DEC-4 | Use applied-event idempotency plus one atomic replay operation for score deltas. | Decided | Supports safe retries from cache flush workflows. | Event IDs must stay unique within a language-pair scope. |
| DEC-5 | Expose cross-package sync behavior through shared `core` contracts rather than concrete cache-specific types. | Decided | Keeps `database` as the default implementation without forcing consumers to type against one concrete class. | Snapshot/export behavior must stay aligned with the shared DTOs and ports in `core`. |
| DEC-6 | Keep personal-vocabulary delete scoped to per-user membership and scores only. | Decided | Shared corpus ownership stays stable and safe for other users. | Deletes do not reclaim canonical word rows or detailed-word rows. |
| DEC-7 | Define exercise progress explicitly per exercise type as `negative_words / total_words * 100`. | Decided | Score ownership is per exercise table and implicit averaging would hide behavior. | Callers choose how to present one or many exercise summaries. |
| DEC-8 | Detailed-word rows live in pair-specific tables with versioned JSON payloads. | Decided | Supports many POS models without table explosion. | Parser/version compatibility becomes a first-class constraint. |
| DEC-9 | Inject the detailed extractor instead of constructing `extract_word_details` internally. | Decided | Same dependency-injection pattern as the translator. | Callers opt into automatic extraction explicitly. |
| DEC-10 | `get_or_extract_details()` fails if the source word is missing from the canonical corpus. | Decided | Avoids silent corpus mutation and keeps persistence fail-fast. | Callers must persist or resolve words before requesting details. |
| DEC-11 | Expose cache-facing detailed reads through the same typed store contract used by other callers. | Decided | Avoids a second remote shape for the same data. | `database_cache` depends on `DetailedWordStore`, not on ad hoc SQL. |

### Consistency Rules

- CR-1: `create_tables(exercise_slugs)` and `ExerciseProgressStore(exercise_types)` must stay aligned on exercise slug naming.
- CR-2: When the module promises multi-language flexibility, helper defaults and schema bootstrap paths must not quietly hardcode only one pair.
- CR-3: Personal-vocabulary reads and cache snapshots must use the same ordering and field set, including `added_at`.
- CR-4: `DetailedWordStore` must round-trip payloads through the same schema registry and version parser defined by `extract_word_details`.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, DEC-1, DEC-3 | QA-1 |
| FR-4, FR-8 | IF-3, DEC-2, DEC-4, DEC-5, DEC-7, CR-1 | QA-2 |
| FR-5 | IF-4, DEC-2 | QA-3 |
| FR-7, FR-10 | IF-1, IF-3, DEC-5, CR-3 | QA-4 |
| FR-9 | IF-1, IF-4, DEC-6 | QA-5 |
| FR-11, FR-12, FR-13, FR-14 | IF-2, IF-6, DEC-8, DEC-9, DEC-10, CR-4 | QA-6 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `DatabaseService` persists canonical words, associates them with users, and returns translated `WordPair` results only when translations exist.
- AC-2: `ExerciseProgressStore` exposes score-aware snapshots with stable remote IDs plus idempotent score replay for configured exercises.
- AC-3: Remote schema bootstrap remains idempotent for the current table set, including the new detailed-word table.
- AC-4: The module can return the full translated personal vocabulary for a user, including `added_at` and per-exercise scores.
- AC-5: The module can report per-exercise negative-balance percentages over the user's translated personal vocabulary.
- AC-6: Deleting one or many personal-vocabulary entries removes only per-user membership and scores.
- AC-7: `DetailedWordStore` returns persisted detailed rows when present and extracts+persists only misses when an extractor is injected.
- AC-8: Invalid detailed payloads, missing source words, and unsupported schema versions fail fast instead of being coerced or silently created.
- AC-9: `database_cache` can consume the typed detailed-word store contract without private SQL knowledge.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest` suites, with integration/e2e tests running against a real Neon database under Doppler-managed configuration.
- Keep remote reset helpers confined to tests.

**Unit:**

- Mock-backend coverage for deduplication, warnings, progress logic, validation, replay semantics, detailed-word store validation, and injected dependency behavior.

**Integration:**

- Real Neon schema creation, CRUD operations, score table behavior, personal-vocabulary joins, delete semantics, snapshot/export correctness, detailed-word persistence, and get-or-extract behavior.

**Contract:**

- Validate idempotent replay, personal-vocabulary DTO shape, exercise-type validation paths on `ExerciseProgressStore`, and detailed payload schema parsing plus schema-version enforcement through the extractor-owned registry.

**E2E or UI Workflow:**

- Full flow from adding words to translated reads, full personal-vocabulary reads, progress summaries, deletes, and persisted score updates.
- Persist source words, request details twice, and verify the second call reuses durable data instead of re-extracting.

**Operational or Non-Functional:**

- Manual verification of Doppler/Neon configuration before running integration or e2e suites.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Unit + E2E | Deduplication and add/read flow tests | PR CI / nightly | Covers the main write/read contract. |
| QA-2 | FR-4 | Unit + Integration | Progress-store validation and snapshot/replay tests | PR CI / nightly | Protects sync-facing behavior. |
| QA-3 | FR-5 | Integration | Table-creation idempotency tests | PR CI / nightly | Verifies remote bootstrap behavior, including detailed-word table. |
| QA-4 | FR-7, FR-10 | Unit + Integration | Personal-vocabulary read-model and enriched snapshot tests | PR CI / nightly | Covers `added_at`, stable IDs, and per-exercise score maps. |
| QA-5 | FR-9 | Integration + E2E | Single-item and bulk delete tests over user membership and scores | PR CI / nightly | Confirms deletes do not remove shared corpus rows. |
| QA-6 | FR-11, FR-12, FR-13, FR-14 | Unit + Integration | Detailed-word persistence and get-or-extract tests | PR CI / nightly | Covers the new storage surface. |

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
| RISK-2 | Event-id idempotency is scoped per language pair, not per exercise. | Reused event IDs across exercises could collide. | Keep event IDs globally unique per flush event. |
| RISK-3 | Pair-specific detailed schemas multiply storage and migration complexity as new target languages are added. | Operational footprint grows quickly. | Keep pair-specific tables and schema versioning from day one. |
| RISK-4 | The extractor field matrix for some POS is not finalized yet. | Detailed-word rows may drift before the model contract stabilizes. | Finalize the per-POS field matrix before implementation. |

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
| RV-3 | A-3 | Not yet reviewed | Kept as active assumption | A-3 |
| RV-4 | A-4 | Approved | Promoted into explicit detailed-word storage rules | FR-12, BR-8 |

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

## 5. Tiered Mixed-Exercise Extension

### Change Summary

This extension adds a dedicated remote persistence surface for the new tiered mixed-exercise mode while leaving the current `ExerciseProgressStore`, score tables, and per-exercise progress summaries unchanged. The preferred implementation path is additive: reuse the existing per-exercise score tables, add one dedicated repeat-state table for tiered mode, and expose a separate tiered store/API rather than broadening legacy methods.

### Tiered Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| TFR-DB-1 | The module must add a dedicated `TieredExerciseProgressStore(user_id, source_language, target_language, mode_slug, exercise_types, backend?)` or equivalent additive API. | Must | Keeps the current `ExerciseProgressStore` contract untouched. |
| TFR-DB-2 | The module must persist tiered repeat state in a dedicated remote table named `user_word_tiered_repeat_state_<src>_<tgt>` or equivalent, keyed by `(mode_slug, user_id, source_word_id)`. | Must | Row presence means the word is currently in repeat mode for that tiered configuration. |
| TFR-DB-3 | Tiered mode must continue using the existing `user_word_exercise_scores_<src>_<tgt>_<exercise>` tables for score ownership and mutation. | Must | Answering a tiered exercise affects that exercise score exactly as usual. |
| TFR-DB-4 | The tiered store must expose candidate reads containing `WordPair`, `source_word_id`, ordered per-exercise scores, and repeat-state for all translated user words in the configured mode. | Must | Required by the tiered sampler. |
| TFR-DB-5 | The tiered store must expose a mixed progress summary where a word counts as positive only if every participating exercise score is `> 0`. | Must | User-confirmed aggregate rule. |
| TFR-DB-6 | The tiered store must expose idempotent answer replay that updates the answered exercise score and repeat-state atomically for one event. | Must | Needed for safe cache flush/retry behavior. |
| TFR-DB-7 | The tiered remote snapshot for cache rebuilds must include ordered scores plus repeat-state for each word in the configured mode. | Must | Prevents cache-side re-derivation from incomplete data. |
| TFR-DB-8 | Existing `ExerciseProgressStore.get_progress_summary()` and current per-exercise negative-balance reports must remain unchanged. | Must | User explicitly requested no regression in current progress reports. |

### Tiered Rules and Invariants

- TBR-DB-1: A tiered configuration is identified by `mode_slug` plus the ordered participating exercises, and the same `mode_slug` must not be reused for a different order.
- TBR-DB-2: Missing scores are treated as `0` for tiered candidate selection and aggregate positive-progress calculation.
- TBR-DB-3: A wrong answer while not already in repeat mode must activate repeat mode for that `(mode_slug, user_id, source_word_id)`.
- TBR-DB-4: A correct answer while in repeat mode must clear repeat mode for that `(mode_slug, user_id, source_word_id)`.
- TBR-DB-5: A wrong answer while already in repeat mode must keep repeat mode only while at least one participating exercise remains positive after the score update; otherwise repeat mode must be cleared.
- TBR-DB-6: Persisted repeat-state without any positive participating score is invalid and must surface as an explicit error instead of being normalized silently.

### Tiered Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| TIF-DB-1 | Python API | Inbound | `sampling`, `database_cache` | `get_tiered_candidates()`, `get_tiered_progress_summary()`, `export_tiered_snapshot()`, `apply_tiered_result(...)` | Additive tiered remote surface. |
| TIF-DB-2 | Storage | Internal | Neon PostgreSQL | Existing per-exercise score tables plus `user_word_tiered_repeat_state_<src>_<tgt>` | One dedicated table for tiered-mode state. |
| TIF-DB-3 | Change reference | Outbound | `sampling` | Tiered candidate-provider contract and selection semantics | See the sampling tiered extension section. |
| TIF-DB-4 | Change reference | Outbound | `database_cache` | Tiered cache refresh/flush contract | See the database_cache tiered extension section. |

### Tiered Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| `user_word_tiered_repeat_state_<src>_<tgt>` | Owned | Repeat-mode rows keyed by `mode_slug`, `user_id`, and `source_word_id`. | Durable remote state | Row presence means repeat mode is active. |
| Tiered candidate snapshot | Owned | Read-model combining translated pairs, ordered scores, and repeat-state. | Runtime or export payload | Built from existing score tables plus tiered repeat rows. |
| Tiered aggregate progress summary | Owned | Completion summary where "positive" means all participating scores are `> 0`. | Runtime per request | Separate from existing per-exercise negative reports. |

### Tiered Processing Flow

1. Table creation bootstraps the dedicated tiered repeat-state table in addition to the existing score and event tables.
2. Tiered candidate reads join translated user words with existing per-exercise scores and the dedicated repeat-state table for the configured `mode_slug`.
3. Aggregate tiered progress counts a word as completed only when every participating exercise score is strictly positive.
4. Tiered answer replay applies the score delta to the answered exercise table, derives the next repeat-state using the configured mode rules, updates the repeat-state table, and records the event atomically.

### Tiered Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| TDEC-DB-1 | Keep existing per-exercise score tables as the canonical score source for tiered mode. | Decided | Avoids duplicate score ownership and preserves existing semantics. | Tiered logic is an overlay, not a new scoring system. |
| TDEC-DB-2 | Persist only tiered repeat-state in the new dedicated table. | Decided | This is the only new durable state that cannot be derived from scores alone. | Tiered schema change stays minimal. |
| TDEC-DB-3 | Add a separate tiered store/API instead of widening `ExerciseProgressStore`. | Decided | Lowest-risk path that preserves current callers and tests. | Tiered callers opt into a new remote surface. |
| TDEC-DB-4 | Keep mixed aggregate progress separate from current per-exercise negative-progress reporting. | Decided | User requested that existing reports remain unchanged. | The module exposes two distinct progress-summary concepts. |

### Tiered Validation

**Acceptance Criteria:**

- TAC-DB-1: Existing `ExerciseProgressStore` reads, summaries, and score replay behavior remain unchanged.
- TAC-DB-2: Tiered remote reads expose ordered scores plus repeat-state for each translated user word.
- TAC-DB-3: Tiered answer replay updates the answered exercise score and repeat-state atomically and idempotently.
- TAC-DB-4: Mixed progress summary counts a word as positive only when all participating exercise scores are `> 0`.

**Testing Strategy:**

- Unit: transition matrix for normal vs repeat mode, aggregate positive-progress math, `mode_slug` validation, and invalid persisted repeat-state detection.
- Integration: schema creation for the dedicated repeat-state table, candidate reads, snapshot export, and atomic tiered replay on a real backend.
- Contract: cache-facing tiered snapshot and replay behavior must stay compatible with the tiered cache implementation.

### Tiered Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| TRISK-DB-1 | Remote repeat-state transitions and local cache transitions could diverge. | The same answer sequence could produce different next exercises locally vs remotely. | Share one explicit transition matrix in tests across `database` and `database_cache`. |
| TRISK-DB-2 | `mode_slug` reuse with a different exercise order would corrupt tiered behavior. | Persisted repeat-state could be interpreted against the wrong complexity ordering. | Validate `mode_slug` plus ordered exercises at construction and refresh time. |

### Tiered Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| TOQ-DB-1 | Should the tiered snapshot export duplicate full word-pair data, or should the future cache path compose tiered repeat-state with the existing practice snapshot? | Open | Decide during implementation after comparing isolation vs local duplication costs | The additive low-risk path is to allow a dedicated tiered snapshot first. |
