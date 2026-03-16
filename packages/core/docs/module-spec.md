---
title: "nl_processing.core Module Spec"
module_name: "nl_processing.core"
document_type: "module-spec"
related_docs: []
---

# Module Spec: nl_processing.core

> This spec describes the target-state public contract for `nl_processing.core`.
> It defines WHAT the module must provide, not HOW it is implemented.
> Only documented public surfaces in this file are supported.

## 1. Module Snapshot

### Summary

`nl_processing.core` is the shared foundation package for repository-wide value types, a small set of fail-fast exceptions, one canonical protocol surface, and reusable prompt and image helpers. It exists to provide stable, module-agnostic contracts that are broadly reusable across packages without carrying package-specific storage, sync, or workflow semantics.

The target state intentionally simplifies the module. Core keeps only public types and protocols that represent clear cross-package concepts, and removes legacy or overlapping contract surfaces that encode database-specific behavior, duplicated models, or derivable summaries.

### System Context

`nl_processing.core` sits at the bottom of the internal package dependency graph. Other packages may import its shared enums, models, exceptions, prompt helpers, image helpers, and canonical protocol definitions. `core` must remain free of sibling-package business rules, storage details, transport concerns, and package-local workflow contracts.

### In Scope

- Canonical shared enums and Pydantic models used across packages
- Canonical shared exception types
- One canonical protocol namespace for supported cross-package protocols
- Prompt-loading and generic LLM helper utilities
- Image validation, encoding, and multimodal message helpers
- Explicit definition of which legacy protocol and progress-model surfaces are not part of the supported contract

### Out of Scope

- Database-specific read, sync, delete, cache, or persistence contracts
- Detailed-record extraction and payload-validation contracts tied to one downstream workflow
- Derived progress summaries or convenience read models that callers can compute themselves
- HTTP, CLI, env-var, secret, and infrastructure concerns
- Package-specific NLP pipelines and business logic

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Backward compatibility is not required for this cleanup and target-state redesign. | Approved | Explicit user direction |
| A-2 | No active consumer requires the current `database_*`-style progress or detailed-record contract shapes from `core`. | Approved | Explicit user direction |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | Provide `Language` as the canonical shared language enum with members `Language.NL = "nl"` and `Language.RU = "ru"`. | Must | Shared cross-package identifier set |
| FR-2 | Provide `PartOfSpeech` as the canonical shared grammatical-category enum. | Must | Existing values remain explicit enum members |
| FR-3 | Provide `ExtractedText` with required field `text: str`. | Must | Shared text-extraction value object |
| FR-4 | Provide `Word` with required fields `normalized_form`, `word_type`, and `language`. | Must | Canonical word-level value object |
| FR-5 | Provide `WordPair` with required `source` and `target` `Word` values. | Must | Canonical bilingual pair model |
| FR-6 | Provide `ScoredWordPair` as the canonical score-bearing pair model for workflows that need scores but do not need persistent identity or lifecycle metadata. | Must | Minimal transient scoring model |
| FR-7 | Provide `WordPairSnapshot` as the only public persistent/snapshot word-pair model in `core`. It must represent the canonical stored word-pair snapshot and include stable word identifiers, score state, and required `added_at` record-creation timestamp in addition to the pair data. | Must | Replaces duplicate progress-oriented models |
| FR-8 | Provide one canonical public protocol module at `nl_processing.core.protocols`. | Must | `core` must not fragment protocols across multiple public files |
| FR-9 | Retain only protocol definitions in `core` that express clear module-agnostic contracts. The supported target-state protocol surface is `ScoredPairProvider`, with async method `get_word_pairs_with_scores(self) -> list[ScoredWordPair]`. | Must | Current minimal protocol contract |
| FR-10 | Provide `load_prompt(prompt_path)` that loads LangChain-native JSON and returns `ChatPromptTemplate`. | Must | Shared prompt-loading contract |
| FR-11 | Provide `ChatOpenAIKwargs` and `build_llm_kwargs(model, service_tier, reasoning_effort, temperature)` as generic LLM configuration helpers that omit unset optional keys. | Must | Shared prompt/model utility |
| FR-12 | Provide image helper functions for supported suffix validation, base64 encoding, synthetic image generation, synthetic image data-URL generation, multimodal human image messages, and generic AI tool-call messages. | Must | Existing shared helper scope remains public |
| FR-13 | Provide distinct public exception types `APIError`, `UnsupportedImageFormatError`, `TargetLanguageNotFoundInInputError`, and `UnsupportedLanguageError`. | Must | Shared fail-fast error taxonomy |
| FR-14 | Remove duplicate or legacy public model and protocol surfaces from the supported contract rather than preserving them for compatibility. | Must | Explicit cleanup requirement |

### Rules and Invariants

- BR-1: `core` exposes a single canonical protocol namespace: `nl_processing.core.protocols`.
- BR-2: `core` does not expose a supported umbrella re-export module for protocols or ports.
- BR-3: `ScoredPairProvider` remains runtime-checkable and structurally typed.
- BR-4: `WordPairSnapshot` is the canonical snapshot/read model for persisted or synced word-pair state in `core`, and `added_at` is part of its required contract.
- BR-5: `EnrichedWordPairSnapshot`, `PersonalWord`, and `ExerciseProgressSummary` are not part of the supported target-state `core` contract.
- BR-6: `DetailedWordRecordPort`, `DetailedWordExtractorPort`, `WordExtractorPort`, `PayloadValidatorPort`, `RemoteProgressSyncPort`, and `RemoteDeletePort` are not part of the supported target-state `core` contract.
- BR-7: `core` must not keep overlapping public models that carry the same underlying word-pair record with only naming or minor-shape differences.
- BR-8: Aggregated progress summaries are caller-derived views, not canonical `core` models, unless a future module spec proves they are required as shared contract surface.
- BR-9: Prompt and image helpers remain generic and package-agnostic; they must not encode package-specific storage or workflow semantics.
- BR-10: Public helpers and models fail fast on invalid inputs and do not hide errors with fallback behavior.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Architecture clarity | Public `core` contracts must be minimal, non-overlapping, and named by domain meaning rather than implementation history. | No duplicate public surfaces for the same concept | Primary cleanup goal |
| NFR-2 | Modularity | `core` public contracts must stay module-agnostic. | No database-, cache-, or transport-specific protocol semantics in `core` | Prevents contract drift |
| NFR-3 | Reliability | Public helpers and models must fail fast on invalid input, invalid files, and invalid enum/model values. | No silent fallback behavior | Repo-wide rule |
| NFR-4 | Compatibility | Python runtime compatibility | `>=3.12` | From package configuration |
| NFR-5 | Compatibility | Pydantic compatibility | `>=2.0,<3` | Shared model layer |
| NFR-6 | Compatibility | LangChain Core compatibility | `>=0.3,<1` | Prompt/message helpers |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Notes |
| --- | --- | --- | --- |
| FM-1 | A caller imports or depends on a removed legacy protocol or model surface. | That surface is unsupported in the target-state contract and must not be treated as public API. | Breaking cleanup is intentional |
| FM-2 | A caller needs aggregate progress summaries. | The caller derives them from canonical record data rather than importing a shared summary model from `core`. | Keeps `core` minimal |
| FM-3 | A caller needs persistent word-pair record data with timestamps. | `WordPairSnapshot` is the single supported `core` record shape for that use case, including required `added_at`. | Avoids duplicate snapshot/read models |
| FM-4 | `load_prompt` receives missing, malformed, or non-prompt input. | Raise explicit file, JSON, or type errors. | No fallback parsing |
| FM-5 | Public models receive invalid enum values or missing required fields. | Raise `ValidationError`. | Standard Pydantic behavior |
| FM-6 | Image helpers receive unsupported formats, missing files, or encoding failures. | Raise explicit helper or underlying I/O/encoding errors. | Fail-fast behavior |

## 3. Public Contract

### Responsibilities and Boundaries

**Responsible For:**

- Canonical shared enums and value models
- Canonical shared exceptions
- One canonical protocol surface for truly cross-package contracts
- Generic prompt and image helper utilities
- Declaring which legacy visible surfaces are non-contract and unsupported

**Not Responsible For:**

- Database progress-sync/delete protocols
- Detailed-record extraction or payload-validation contracts
- Derived summary/reporting models
- Storage schemas, migrations, cache refresh logic, or transport-layer concerns

### Public Interfaces

| ID | Interface Type | Direction | Counterparty | Contract Summary | Expected Behavior |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python import | Outbound | Any consumer package | `nl_processing.core.models.Language`, `PartOfSpeech`, `ExtractedText`, `Word`, `WordPair`, `ScoredWordPair`, `WordPairSnapshot` | Imports provide the canonical shared model surface; no duplicate progress/read models are supported alongside `WordPairSnapshot`. |
| IF-2 | Python import | Outbound | Any consumer package | `nl_processing.core.protocols.ScoredPairProvider` | Provides the only supported public protocol contract in `core`: an async scored-pair provider returning `list[ScoredWordPair]`. |
| IF-3 | Python import | Outbound | Any consumer package | `nl_processing.core.prompts.load_prompt`, `ChatOpenAIKwargs`, `build_llm_kwargs(...)`, `build_tool_call_ai_message(...)` | Shared prompt/model/message helpers remain generic and fail fast on invalid inputs. |
| IF-4 | Python import | Outbound | Any consumer package | `nl_processing.core.image_encoding` helpers | Shared image validation, encoding, synthetic image, data-URL, and multimodal message helpers remain public. |
| IF-5 | Python import | Outbound | Any consumer package | `nl_processing.core.exceptions` public exception classes | Shared exceptions remain distinct catch targets with explicit semantics. |

### Internal and Non-Contract Notes

- `nl_processing.core.ports`: not part of the supported target-state contract; callers must not rely on protocol re-exports from an umbrella ports module.
- `nl_processing.core.progress_ports`: not part of the supported target-state contract.
- `nl_processing.core.progress_models`: not part of the supported target-state contract as a separate public model namespace.
- Any `detail_ports`-style surface in `core`: not part of the supported target-state contract.
- Any protocol or model surface not explicitly listed in this spec is internal, legacy, or unsupported.

### External Dependencies and Constraints

| ID | Dependency or Constraint | Why It Matters | Behavioral Assumption or Limit | Notes |
| --- | --- | --- | --- | --- |
| EC-1 | Pydantic v2 | All public models rely on standard validation and serialization behavior. | Validation failures surface directly to callers. | Shared model foundation |
| EC-2 | LangChain Core | Prompt and message helpers produce/consume LangChain-native prompt and message objects. | `load_prompt` expects LangChain-serialized prompt JSON. | Prompt contract |
| EC-3 | OpenCV and NumPy | Image helpers rely on OpenCV/NumPy-based image processing. | Image encoding helpers surface native failures. | Image utility scope |

### Cross-Module Change References

| Affected Module | Why It Must Change | External Spec or Doc Reference | Ownership Status |
| --- | --- | --- | --- |
| `packages/database`, `packages/database_cache`, and any consumer of removed progress/detail contracts | Consumers of removed or merged `core` protocol/model surfaces must migrate to the new minimal contract or own their module-specific contracts locally. | Their module-local specs must define any non-core storage, cache, or workflow contracts. | Needs follow-up outside `core` |

### Compatibility Notes

| ID | Area | Expectation | Impact if Broken | Notes |
| --- | --- | --- | --- | --- |
| COMP-1 | Legacy protocol/model surfaces | Backward compatibility is not required for removed `core` progress/detail/ports surfaces. | Existing imports may break and must migrate. | Intentional redesign |
| COMP-2 | Canonical protocol entry point | Supported protocols are imported from `nl_processing.core.protocols` only. | Re-export-based imports are unsupported. | Simplifies public contract |
| COMP-3 | Canonical snapshot model | `WordPairSnapshot` is the sole supported persisted/snapshot record model in `core`, with required `added_at` as part of the canonical snapshot shape. | Callers relying on duplicate record models or optional timestamp semantics must consolidate. | Simplifies data surface |

## 4. Acceptance and Validation

### Acceptance Criteria

- AC-1: The `core` spec documents exactly one supported public protocol namespace: `nl_processing.core.protocols`.
- AC-2: The documented target-state protocol contract keeps only `ScoredPairProvider` as the supported `core` protocol surface.
- AC-3: The documented target-state model contract keeps `WordPairSnapshot` as the sole persisted/snapshot record model in `core`, with required `added_at`.
- AC-4: The spec explicitly marks `ports.py`, fragmented progress/detail protocol files, duplicate record models, and derived summary models as unsupported target-state contract surfaces.
- AC-5: Prompt, image, exception, enum, and shared value-model sections remain documented consistently with the simplified contract.
- AC-6: The spec reflects a breaking cleanup target state directly and does not preserve legacy contracts merely because they existed before.

### High-Level Validation Coverage

| ID | Target | What Must Be True | Observable Evidence or Result |
| --- | --- | --- | --- |
| VAL-1 | FR-7, BR-4, BR-7 | `WordPairSnapshot` is documented as the only canonical persisted/snapshot word-pair record, and `added_at` is required in that contract. | No parallel `core` record model is described as public and no ambiguity remains about timestamp ownership. |
| VAL-2 | FR-8, FR-9, BR-1, BR-2 | Public protocol support is consolidated into one canonical module. | The spec names `nl_processing.core.protocols` as the only supported protocol namespace. |
| VAL-3 | BR-5, BR-6, AC-4 | Removed legacy progress/detail surfaces are clearly unsupported. | The spec explicitly lists them as non-contract. |
| VAL-4 | FR-10 to FR-13 | Unrelated shared helper and exception surfaces remain internally consistent after the cleanup. | Prompt, image, and exception sections still describe supported public behavior. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Some downstream packages may still import removed or undocumented `core` progress/detail surfaces. | Breaking cleanup may require coordinated follow-up changes outside `core`. | Treat this spec as the source of truth and update dependent modules to own non-core contracts locally. |
| RISK-2 | The exact future home of storage-specific or workflow-specific contracts is outside this spec. | Follow-up module specs may be needed before implementation work begins in those modules. | Document ownership in the relevant downstream module rather than restoring those contracts to `core`. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Approved | Promoted into explicit breaking-change compatibility note. | COMP-1 |
| RV-2 | A-2 | Approved | Promoted into explicit removal of legacy progress/detail contract surfaces from `core`. | BR-5, BR-6 |

### Decision Outcomes

| ID | Source | Resolution Status | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-3 | Prior open question on `WordPairSnapshot.added_at` | Resolved | `added_at` is required as part of the canonical `WordPairSnapshot` contract for every persisted/snapshot record represented by `core`. | FR-7, BR-4, COMP-3, AC-3 |

### Deferred Work

- D-1: Update downstream module specs that currently rely on removed or merged `core` progress/detail contracts.
