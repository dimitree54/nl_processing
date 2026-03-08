---
title: "core Module Spec"
module_name: "core"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
---

# Module Spec: core

## 1. Module Snapshot

### Summary

`core` is the shared contract package for `nl_processing`. It centralizes cross-package enums, Pydantic models, behavioral protocols, exceptions, and prompt-loading helpers so that the rest of the repository can exchange data through stable public types instead of private module-specific shapes. It intentionally keeps domain logic thin and reusable.

### System Context

`core` is the foundational dependency for the extract, translate, database, database_cache, and sampling modules. It does not own any product workflow by itself; instead, it supplies the typed interfaces, shared behavioral ports, and prompt-chain utilities that let the other modules compose compatible implementations.

### In Scope

- Shared enums, Pydantic models, and behavioral protocols used across package boundaries.
- Shared exceptions for common API/image-language error cases.
- Prompt loading from serialized LangChain JSON assets.
- Shared translation-chain construction for pair-based translation modules.

### Out of Scope

- Module-specific service logic or prompt contents.
- Storage backends, caches, or business workflows.
- Package-specific validation rules that do not cross module boundaries.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Cross-package DTOs will continue to live in `core` instead of being duplicated in feature packages. | Needs Review | Matches the current dependency structure. |
| A-2 | LangChain-serialized JSON prompt assets remain the chosen prompt packaging format. | Needs Review | `load_prompt()` depends on this contract. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | `core.models` must expose shared public enums and DTOs for languages, parts of speech, extracted text, words, word pairs, scored word pairs, and remote sync snapshots. | Must | `WordPairSnapshot` extends `ScoredWordPair` with stable remote source and target IDs for cache refresh. |
| FR-2 | `core.exceptions` must expose shared exception types for upstream API failures and image/language extraction failures. | Must | Imported by the LLM-facing modules. |
| FR-3 | `load_prompt(prompt_path)` must load a LangChain `ChatPromptTemplate` from a JSON file and fail fast on missing or malformed prompt assets. | Must | Common prompt contract. |
| FR-4 | `build_translation_chain(...)` must validate the requested language pair, load the correct prompt JSON, bind the tool schema, and return a runnable translation chain. | Must | Shared translation infrastructure. |
| FR-5 | `core.ports` must expose shared protocol types for score-aware pair providers and remote progress synchronization. | Must | Used by `sampling`, `database`, and `database_cache`. |

### Rules and Invariants

- BR-1: Shared public models use Pydantic and enums so downstream packages get runtime validation plus stable JSON representations.
- BR-2: Prompt loading accepts only serialized JSON objects that deserialize to `ChatPromptTemplate`.
- BR-3: Translation language-pair validation happens before a translation chain is used.
- BR-4: Cross-package behavioral ports belong in `core` when multiple modules must type against the same contract.
- BR-5: `core` must not accumulate package-specific business rules that belong in feature modules.
- BR-6: Shared sync DTOs should capture the stable identifiers consumers need so cache or sampling modules do not invent backend-specific placeholders.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Type Safety | Shared interfaces must stay fully typed and validation-backed. | Pydantic models + enums on public contracts | Prevents silent schema drift. |
| NFR-2 | Reliability | Prompt and language-pair failures must fail fast with descriptive exceptions. | No silent fallbacks | Critical for debugging package modules. |
| NFR-3 | Compatibility | `core` must remain lightweight and reusable across all package modules. | No storage/runtime side effects | Keeps dependency fan-out safe. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Prompt file is missing. | `FileNotFoundError` is raised immediately. | Fix packaging or prompt path. |
| FM-2 | Prompt JSON is malformed or not a prompt object. | `ValueError` or `TypeError` is raised immediately. | Regenerate or repair the prompt asset. |
| FM-3 | Unsupported translation pair is requested. | `ValueError` is raised before chain use. | Update `_SUPPORTED_PAIRS`, prompt assets, and tests together if support is added. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Shared enums, DTOs, and behavioral ports crossing package boundaries.
- Shared exceptions used by multiple modules.
- Prompt-loading and translation-chain helpers.

**Does Not Own:**

- Module-specific services, prompts, or benchmarks.
- Remote/database/caching state.
- Language-specific business rules beyond shared contracts.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Outbound | All package modules | `Language`, `PartOfSpeech`, `ExtractedText`, `Word`, `WordPair`, `ScoredWordPair`, `WordPairSnapshot` | Main shared DTO contract surface, including cache-refresh snapshots with both remote IDs. |
| IF-2 | Python API | Outbound | `database`, `database_cache`, `sampling`, and tests | `ScoredPairProvider`, `RemoteProgressSyncPort` | Shared behavioral contract surface for score reads and remote cache sync. |
| IF-3 | Python API | Outbound | Translation modules | `build_translation_chain(...)` | Shared translation-chain builder. |
| IF-4 | File contract | Inbound | Prompt asset packages | LangChain JSON prompt files | Consumed by `load_prompt()`. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Shared enums/models | Owned | Cross-package data contracts. | Versioned with the repo | Must stay backward-compatible where practical. |
| Shared exceptions | Owned | Common failure types for multiple modules. | Versioned with the repo | Keep semantics stable. |
| Prompt-loading helpers | Owned | Utilities for loading and composing prompt chains. | Versioned with the repo | Reused by translation modules. |
| Prompt assets themselves | Referenced | JSON files shipped by other modules. | Owned by feature packages | `core` loads them but does not define their content. |

### Processing Flow

1. A consumer imports shared enums/models or exceptions from `core`.
2. For prompt-based modules, the consumer calls `load_prompt()` or `build_translation_chain(...)`.
3. `build_translation_chain(...)` validates the pair, loads the prompt asset, binds the tool schema, and returns a ready runnable.
4. Feature modules execute the chain and map results back into shared `core` models.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep shared DTOs, enums, and narrow cross-package ports in `core`. | Decided | Prevents packages from depending on each other's private models or duplicating protocol definitions. | Shared contracts must evolve here first. |
| DEC-2 | Centralize prompt loading and translation-chain creation. | Decided | Removes duplicated LangChain setup from translation packages. | Prompt asset shape must stay compatible with `core` helpers. |
| DEC-3 | Keep shared models thin and generic. | Decided | Allows feature modules to compose behavior without overfitting the base package. | Rich feature-specific fields stay outside `core` until widely shared. |

### Consistency Rules

- CR-1: Shared model changes must be coordinated with downstream prompts/tests when they affect serialized fields or enums.
- CR-2: New translation pairs require updates to both prompt assets and pair validation sets; prompt files alone are not enough.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-1 | IF-1, DEC-1, DEC-3 | QA-1 |
| FR-5 | IF-2, DEC-1, CR-1 | QA-1 |
| FR-3 | IF-4, DEC-2, CR-2 | QA-2 |
| FR-4 | IF-3, DEC-2, CR-2 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: Downstream modules can import shared models, including `WordPairSnapshot`, protocols, and exceptions from `core` without redefining them locally.
- AC-2: Prompt loading fails fast on missing, malformed, or wrong-type prompt JSON files.
- AC-3: Translation modules can build pair-specific chains through `build_translation_chain(...)`.

### Testing Strategy

**Framework and Constraints:**

- Reuse the existing package-local `pytest` unit suite under `packages/core/tests/unit`.
- Keep tests deterministic and local; `core` itself should not require live API calls.

**Unit:**

- Enum/model/protocol validation and serialization.
- Exception construction and distinct exception typing.
- Prompt loading round trips and error cases.

**Integration:**

- N/A for now; integration happens through consuming modules.

**Contract:**

- Validate that `build_translation_chain(...)` rejects unsupported pairs and returns a runnable for supported ones.

**E2E or UI Workflow:**

- N/A for `core` itself.

**Operational or Non-Functional:**

- Static analysis keeps the shared package minimal and typed.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-1 | Unit | Model and enum tests | PR CI | Covers shared schema stability. |
| QA-2 | FR-3 | Unit | Prompt loading error and round-trip tests | PR CI | Protects asset contract. |
| QA-3 | FR-4 | Contract | Translation-chain builder validation tests | PR CI | Confirms supported-pair guardrails. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package `ruff`/`pylint`/`vulture` via package check | Keep shared package small and typed. | PR CI | Lint or dead-code failures. |
| SC-2 | Package unit tests | Preserve shared contract behavior. | PR CI | Schema, prompt, or exception regressions. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Cross-package contract changes | Downstream impact is distributed across modules. | Review consuming packages when changing shared enums/models. | Matching downstream updates in the same change. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Shared enum or model changes drift from prompt instructions and tests. | LLM modules can start failing validation or returning inconsistent data. | Update prompts and module tests together with shared contract changes. |
| RISK-2 | `core` accumulates feature-specific helpers. | The package becomes a dumping ground and increases coupling. | Keep new additions limited to truly shared contracts/utilities. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Which future utilities truly belong in `core`, and which should remain inside feature packages? | Open | Decide during future refactors | Current shared surface is still intentionally small. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending future shared-utility changes | Review during the next cross-module refactor |

### Deferred Work

- D-1: Revisit whether more shared utilities should move into `core` once multiple feature packages need them.
