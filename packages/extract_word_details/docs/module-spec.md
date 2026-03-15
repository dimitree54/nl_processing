---
title: "extract_word_details Module Spec"
module_name: "extract_word_details"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
  - "../../translate_word/docs/module-spec.md"
  - "../../database/docs/module-spec.md"
  - "../../database_cache/docs/module-spec.md"
---

# Module Spec: extract_word_details

## 1. Module Snapshot

### Summary

`extract_word_details` enriches source words with language-learning data that is too rich for the shared `Word` model used by `translate_word`. Its public input stays `list[Word]`, but the output is a discriminated union of pair-specific, part-of-speech-specific detailed models. V1 supports only `nl -> ru`, and all explanatory text is Russian while source lexical material remains Dutch.

### Package and Documentation Location

**Python package path:**

- `packages/extract_word_details/src/nl_processing/extract_word_details/`

**Local module doc path:**

- `packages/extract_word_details/docs/module-spec.md`

**External references allowed:**

- Root repo module spec
- Package-local specs for `core`, `translate_word`, `database`, and `database_cache`
- `database` and `database_cache` module specs are authoritative for persistence and cache behavior

### System Context

The module sits beside `translate_word` and consumes already-normalized `Word` objects produced by upstream extraction or database reads. It owns LLM extraction, typed schemas, prompt assets, and serialization rules. Durable storage and cache behavior for detailed records are owned by the linked `database` and `database_cache` module specs, not by this module.

### In Scope

- Public async extractor for `list[Word]` input.
- Explicit NL->RU detailed models for every current Dutch `PartOfSpeech`.
- Pair-and-POS-specific prompt assets, generator scripts, few-shot examples, and tests.
- Shared serialization contract that downstream persistence consumers can round-trip.

### Out of Scope

- Source-target pairs other than `nl -> ru`.
- POS or language inference.
- User-specific annotations or progress tied to detailed records.
- Persistence layout, table definitions, and cache invalidation rules.
- Generic fallback payloads for unsupported POS.
- Silent recovery from malformed LLM or storage payloads.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Callers provide `list[Word]` with `normalized_form`, `word_type`, and `language` already known. | Approved | Confirmed by user. |
| A-2 | Detailed records are corpus-level but target-language-specific, so `nl -> ru` and future `nl -> en` data are separate. | Approved | Confirmed by user. |
| A-3 | Unsupported or unknown POS are skipped, logged, and omitted from the result. | Approved | Changes the original equal-length contract. |
| A-4 | V1 supports all current Dutch POS values, but only for `nl -> ru`. | Approved | Confirmed by user. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `WordDetailsExtractor(source_language, target_language, model, reasoning_effort, temperature)` and `await extract(words: list[Word]) -> list[DetailedWordRecord]`. | Must | Public input remains `list[Word]`. |
| FR-2 | The extractor must support only `nl -> ru` in V1 and reject other pairs during initialization. | Must | Pair-specific data model. |
| FR-3 | `extract([])` must return `[]` without any LLM call. | Must | Same no-op behavior as `translate_word`. |
| FR-4 | The extractor must require a single source language per batch and must not infer POS; routing is based only on the provided `Word.word_type`. | Must | Mixed-language batches fail fast. |
| FR-5 | Every supported Dutch POS must have its own explicit NL->RU Pydantic model. | Must | No generic dict outputs. |
| FR-6 | Each detailed model must preserve Dutch lexical material and include Russian explanatory content. | Must | Example: Dutch example sentence plus Russian explanation. |
| FR-7 | Unsupported or unknown POS inputs must be skipped with a warning log and omitted from the returned list. | Must | Output order matches the supported input subsequence. |
| FR-8 | Shared learning fields must cover common phrases, example sentences, word-part explanations, and interesting facts; when a meaningful Dutch-Russian parallel exists, `interesting_facts` must surface it. | Must | Example: loanwords, cognates, or historical links between Dutch and Russian. |
| FR-9 | The module must publish one versioned schema registry and serializer contract for all supported detailed models. | Must | Downstream persistence must reuse this contract. |
| FR-10 | Prompt generator scripts and generated prompt assets must exist per supported POS and include few-shot examples plus schema consistency tests. | Must | Prompt scripts are the source of truth. |
| FR-11 | Malformed LLM output and schema mismatches must fail fast with explicit exceptions. | Must | No fallback parsing. |

### Rules and Invariants

- BR-1: The public output type is a discriminated union of explicit detailed models, never raw dict payloads.
- BR-2: Detailed records are source-target specific; the same source word can have separate `nl -> ru` and `nl -> en` records.
- BR-3: Extractor and downstream persistence consumers must share one schema registry and versioning contract.
- BR-4: Returned records preserve the original order of supported inputs only.
- BR-5: Human-readable explanations are stored in the target language for the configured pair.
- BR-6: Interesting facts must include target-language parallels when the parallel is real and relevant; absence of a real parallel is allowed.
- BR-7: Invalid payloads raise explicit errors; they are never coerced into partial records.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Reliability | Schema validation must happen before returning detailed records. | 100% typed parse on fixture payloads | Correctness over convenience. |
| NFR-2 | Performance | Live extraction stays within an acceptable QA budget for representative batches. | Target <60s for 10 supported words | Richer than `translate_word`, so a looser budget is acceptable. |
| NFR-3 | Maintainability | POS logic, schemas, prompts, and tests must be decomposed per POS and avoid monolithic files. | Respect repo file-size rules | All-POS V1 cannot live in one giant module. |
| NFR-4 | Observability | Skips and extraction failures must be logged clearly. | Structured package logs | Output may be shorter than input. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Unsupported pair is requested. | Raise `ValueError` at init. | Add pair-specific schemas, prompts, and tests together. |
| FM-2 | Mixed-language input batch is passed. | Raise `ValueError`. | Caller must batch by source language. |
| FM-3 | Input batch is empty. | Return `[]`. | Valid no-op path. |
| FM-4 | Unsupported or unknown POS is encountered. | Skip item and log warning with reason. | Caller can inspect logs and remaining results. |
| FM-5 | LLM tool payload fails validation or returns inconsistent batch data. | Raise `APIError` and fail the affected extraction call. | Fix prompt/schema; do not fallback. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Pair-specific and POS-specific extraction logic.
- Typed detailed-model definitions and nested usage/explanation schemas.
- Prompt generation assets and schema serialization/parsing logic.

**Does Not Own:**

- Generic word translation.
- POS detection, normalization, or corpus insertion.
- User-specific vocabulary membership or exercise progress.
- Remote or local storage layout.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `await extract(words: list[Word]) -> list[DetailedWordRecord]` | Main extractor surface. |
| IF-2 | Shared types | Inbound | `core` | `Word`, `Language`, `PartOfSpeech`, `APIError`, prompt-loading helpers | Reuses shared lexical DTOs. |
| IF-3 | Asset/API | Outbound | Prompt assets + OpenAI | One prompt/tool schema per `(pair, POS)` | Each POS has dedicated few-shot examples. |
| IF-4 | Shared schema | Outbound | `database`, `database_cache` | Versioned model registry + serializer/parser contract | Persistence details live in those modules. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| POS handler registry | Owned | Maps `(source_language, target_language, word_type)` to model schema, prompt asset, and parser. | Runtime only | Central dispatch point. |
| Prompt assets | Owned | Generated prompt JSON plus few-shot examples per POS. | Versioned with package | Source of extraction quality. |
| Detailed payload schema | Owned | Versioned JSON representation of typed detailed records. | Stable across extractor and persistence consumers | Shared parse/serialize contract. |
| Detailed models | Owned | Public discriminated union plus POS-specific nested types. | Versioned with package | Defines the public contract. |

### Processing Flow

1. The constructor validates the source-target pair and loads the supported POS registry for that pair.
2. `extract()` returns `[]` for empty input, validates single-language input, and partitions the batch into supported and skipped items.
3. Supported words are grouped by POS, and each group is processed by its dedicated prompt/tool schema.
4. Parsed POS-specific records are merged back in the original order of supported inputs; skipped items are logged.
5. Downstream persistence consumers serialize and store the resulting records through the shared schema registry defined here.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | V1 supports only `nl -> ru`. | Decided | User requirement and manageable first scope. | New pairs require new schemas, prompts, and tests. |
| DEC-2 | Each Dutch POS gets an explicit model and dedicated handler. | Decided | The module exists specifically to avoid one generic schema. | Registry-driven composition is required. |
| DEC-3 | Extraction batches are split by POS and processed with POS-specific prompts, not one universal prompt. | Decided | Keeps schemas small and few-shot examples relevant. | A mixed-POS input may trigger multiple LLM calls. |
| DEC-4 | Human-readable explanations are target-language-specific, while source lexical material stays in Dutch. | Decided | Matches the requested pair-specific learning value. | Example structures are bilingual by design. |
| DEC-5 | The extractor owns schema keys and versioned payload parsing, but not table or cache layout. | Decided | Keeps boundaries clean. | Persistence specifics must live in `database` and `database_cache`. |
| DEC-6 | Unsupported or unknown POS are skipped with warning instead of raising per-word. | Decided | Matches user direction. | Callers must not assume input/output length parity. |

### Consistency Rules

- CR-1: Adding a POS requires the model, prompt generator, generated asset, serializer entry, and tests to change together.
- CR-2: Public Python APIs return typed detailed models, never storage JSON.
- CR-3: Downstream persistence must round-trip through the same schema registry and version parser defined here.
- CR-4: Logs must include skipped word form and skip reason whenever output length shrinks.
- CR-5: Invalid payloads fail the call; they do not degrade into partial detail objects.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-1, FR-4, FR-7 | IF-1, DEC-2, DEC-3, DEC-6, CR-4 | QA-1 |
| FR-5, FR-8, FR-10 | IF-3, DEC-2, DEC-4, CR-1 | QA-2 |
| FR-9 | IF-4, DEC-5, CR-3 | QA-3 |
| FR-11 | IF-2, IF-4, CR-5 | QA-4 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `WordDetailsExtractor` accepts `list[Word]` for `nl -> ru`, supports all current Dutch POS via explicit models, and returns typed records in supported-input order.
- AC-2: Unsupported pairs and mixed-language batches fail fast; unsupported POS items are logged and skipped.
- AC-3: Prompt assets and few-shot examples exist per POS, and automated tests verify prompt/schema compatibility.
- AC-4: The module publishes one versioned schema registry that persistence consumers can round-trip without using raw dicts at the public boundary.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest` suites and existing live-API integration/e2e patterns.
- Run Python through `uv`; prompt scripts remain the source of truth for generated assets.

**Unit:**

- Pair validation, single-language validation, POS dispatch, skip logging, serializer round-trip, and supported-input order merge.

**Integration:**

- Live extraction for representative Dutch words covering every current POS.

**Contract:**

- Prompt/schema consistency and schema-version parsing used by persistence consumers.

**E2E or UI Workflow:**

- Request mixed-POS detailed extraction for normalized Dutch words and verify supported outputs remain typed and ordered.

**Operational or Non-Functional:**

- Inspect logs for skipped items, extraction failures, and end-to-end latency on representative batches.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-1, FR-4, FR-7 | Unit | Dispatch, validation, skip-log, and order-merge tests | PR CI | Core public contract. |
| QA-2 | FR-5, FR-8, FR-10 | Unit + Integration | Per-POS schema tests plus live quality smoke cases | PR CI / nightly | All Dutch POS must be covered. |
| QA-3 | FR-9 | Contract | Serializer/parser round-trip tests for persistence consumers | PR CI | Protects shared schema contract. |
| QA-4 | FR-11 | Unit + Contract | Invalid payload and schema-version mismatch tests | PR CI | Enforces fail-fast behavior. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package-local `make check` flow | Preserve structure, lint, dead-code, and duplication quality. | PR CI | Formatting, lint, dead-code, duplication, or package test failures. |
| SC-2 | Prompt asset generation check | Ensure generated prompt JSON matches scripts. | PR CI | Generated asset drift. |
| SC-3 | Package tests | Preserve extractor contract behavior. | PR CI | Unit/integration/e2e failures. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Linguistic usefulness of rich explanations | Quality is broader than exact-string assertions. | Review representative outputs for each POS, especially ambiguous or compound words. | Reviewer notes with sample payloads. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | All-POS V1 creates a large prompt and test surface. | Initial implementation may sprawl or drift. | Enforce per-POS decomposition and registry-based composition. |
| RISK-2 | Pair-specific explanations multiply prompt assets as new target languages are added. | Schema and operational footprint grows quickly. | Keep pair-scoped schemas and generator scripts from the start. |
| RISK-3 | Non-noun and non-verb field sets are less concrete today than noun/verb examples. | Implementation may invent inconsistent schemas. | Finalize per-POS field matrix before coding begins. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | What is the exact required field matrix for each Dutch POS beyond the noun and verb examples already given? | Open | Project owner to finalize before implementation | Needed to make V1 truly all-POS. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Approved | Promoted into explicit interface requirements | FR-1, FR-4 |
| RV-2 | A-2 | Approved | Promoted into pair-specific output rules | FR-6, BR-2, DEC-4 |
| RV-3 | A-3 | Approved | Promoted into skip behavior | FR-7, BR-4, DEC-6 |
| RV-4 | A-4 | Approved | Promoted into V1 scope | FR-2, FR-5, DEC-1, DEC-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-5 | OQ-1 | Unresolved | Keep as implementation blocker for schema authoring | Resolve before coding per-POS models |

### Deferred Work

- D-1: Add source-target pairs beyond `nl -> ru`.
- D-2: Add user-specific notes, mnemonics, or personalization on top of corpus-level detailed records.
