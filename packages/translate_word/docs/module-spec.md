---
title: "translate_word Module Spec"
module_name: "translate_word"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
---

# Module Spec: translate_word

> This spec describes the module's desired target-state behavior and public contract.
> It defines WHAT the module must do, not HOW it is implemented.
> Document all public interfaces that other modules or end users are expected to use.
> Do not document implementation details such as files, internal classes, helper functions, algorithms, tests, or QA procedures unless the user explicitly requires them.
> Internal-only surfaces do not need full spec coverage, but when they could be mistaken for public API they should be marked as internal or non-contract.

## 1. Module Snapshot

### Summary

`translate_word` translates batches of normalized Dutch words or short phrases into Russian and returns the translated results as `Word` objects. It preserves one output per input in the same order and behaves as a batch-oriented translation step in the lexical pipeline. The module's contract is limited to supported language-pair translation, typed output, and explicit failure signaling.

### System Context

The module sits after word extraction and before downstream consumers that store, display, or further process translated lexical items. Callers provide normalized `Word` inputs and receive translated `Word` outputs for the configured language pair. The module depends on shared types and shared translation infrastructure from `core`, but those internals are not part of this module's supported public API.

### In Scope

- Public async translator interface for batch word translation.
- Translation of `list[Word]` to `list[Word]` for supported language pairs.
- Order-preserving one-to-one output behavior.
- Explicit rejection of unsupported language pairs and translation failures.

### Out of Scope

- Support for language pairs outside the declared module contract.
- Persistence, caching, retries, or orchestration outside a single translation request.
- Enrichment such as synonyms, examples, usage notes, or alternate translations.
- Ownership of upstream word extraction or downstream storage behavior.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | The module contract uses `Word` as both the input and output data type. | Approved | This is treated as part of the public contract. |
| A-2 | One-to-one, order-preserving mapping is a required caller-facing guarantee. | Approved | Downstream consumers rely on positional correspondence. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `WordTranslator(source_language, target_language, model, reasoning_effort, temperature)` and `await translate(words: list[Word]) -> list[Word]` as its supported public interface. | Must | Constructor options are part of the caller-facing contract. |
| FR-2 | The module must return exactly one output `Word` for each input `Word`, in the same order as received. | Must | Positional correspondence is part of the module contract. |
| FR-3 | Each output `Word` must represent the configured target language. | Must | Callers must not infer or repair target language themselves. |
| FR-4 | When `translate()` receives an empty input list, it must return an empty list. | Must | Empty input is a valid no-op request. |
| FR-5 | The module must reject unsupported source/target language pairs before translation is attempted. | Must | Unsupported pair handling must fail fast. |
| FR-6 | If translation cannot be completed because of upstream model invocation or response-parsing failure, the module must raise `APIError`. | Must | Callers depend on a stable typed failure contract. |

### Rules and Invariants

- BR-1: The public output type is always `list[Word]`.
- BR-2: The module supports only explicitly declared language pairs.
- BR-3: The module does not persist or cache translation results.
- BR-4: The module does not mutate the caller's input list in place.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Structure | Output must remain machine-usable as typed `Word` objects with stable one-to-one ordering. | Required for downstream pipeline use | This is the key integration constraint. |
| NFR-2 | Reliability | Failure conditions must be surfaced explicitly rather than hidden or silently degraded. | Unsupported pairs fail fast; translation failures raise `APIError` | No fallback behavior is permitted. |
| NFR-3 | Packaging | Required translation prompt assets must be available wherever the module is used. | Assets needed for supported pair operation must ship with the module | Missing required assets are contract-breaking. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Notes |
| --- | --- | --- | --- |
| FM-1 | Unsupported language pair is requested. | Reject the request during translator initialization. | Caller must change configuration or request a supported pair. |
| FM-2 | The input list is empty. | Return `[]`. | No translated items are produced. |
| FM-3 | Translation invocation or response parsing fails. | Raise `APIError`. | Failure must remain explicit to callers. |
| FM-4 | The translation response cannot satisfy one-to-one mapping expectations. | Treat the request as failed rather than returning a partial or ambiguous result. | The module contract does not allow silent contract degradation. |

## 3. Public Contract

### Responsibilities and Boundaries

**Responsible For:**

- Accepting supported batch translation requests from callers.
- Returning translated `Word` results in caller input order.
- Enforcing supported-pair constraints and typed failure behavior.

**Not Responsible For:**

- Extracting or normalizing words before translation.
- Storing, caching, retrying, or deduplicating translation results.
- Defining shared domain models owned by other modules.

### Public Interfaces

| ID | Interface Type | Direction | Counterparty | Contract Summary | Expected Behavior |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Python callers | `WordTranslator(source_language, target_language, model, reasoning_effort, temperature)` | Creates a translator instance for a supported source/target pair and rejects unsupported pairs. |
| IF-2 | Python API | Inbound | Python callers | `await translate(words: list[Word]) -> list[Word]` | Translates each input item into one target-language `Word` and preserves input order. |

Document all public contract surfaces here, including public classes, methods, functions, commands, endpoints, events, or other supported entry points.

### Internal and Non-Contract Notes

- Prompt assets, schema definitions, chain-construction helpers, and model wiring are internal implementation details; callers must not depend on them directly.
- Shared types imported from `core` are external dependencies used by this module, not public extension points owned by this module.

### External Dependencies and Constraints

| ID | Dependency or Constraint | Why It Matters | Behavioral Assumption or Limit | Notes |
| --- | --- | --- | --- | --- |
| EC-1 | Shared `Word`, `Language`, and `APIError` types from `core` | They define the caller-visible input, output, and failure shapes. | Compatibility with those shared contracts is required. | Changes to those types may require coordinated updates. |
| EC-2 | Translation-provider behavior | The module depends on an external model-backed translation step. | The module must surface provider failures explicitly instead of masking them. | No fallback provider behavior is assumed. |
| EC-3 | Supported language-pair configuration | The contract is valid only for explicitly supported pairs. | Unsupported pairs are outside the module contract. | Adding a new pair is a separate spec and implementation change. |

### Cross-Module Change References

| Affected Module | Why It Must Change | External Spec or Doc Reference | Ownership Status |
| --- | --- | --- | --- |
| N/A | No external module change is required by this target-state contract. | N/A | N/A |

### Compatibility Notes

| ID | Area | Expectation | Impact if Broken | Notes |
| --- | --- | --- | --- | --- |
| COMP-1 | Translator API | Public async constructor usage and `translate()` contract remain stable for supported callers. | Callers may need code changes or fail at runtime. | Breaking changes require explicit coordination. |
| COMP-2 | Output ordering | Input/output positional correspondence remains stable. | Downstream consumers may mis-associate translations with source words. | This is a hard compatibility requirement. |
| COMP-3 | Failure typing | Unsupported pairs and translation failures remain explicit and typed. | Callers may be unable to handle failures consistently. | Silent degradation is not compatible behavior. |

## 4. Acceptance and Validation

### Acceptance Criteria

- AC-1: A caller can create a translator only for a supported language pair.
- AC-2: `translate([])` returns `[]`.
- AC-3: For a non-empty valid batch, the module returns one target-language `Word` per input item in the same order.
- AC-4: Unsupported pairs are rejected before translation begins.
- AC-5: Translation invocation or parsing failure is surfaced as `APIError`.

### High-Level Validation Coverage

| ID | Target | What Must Be True | Observable Evidence or Result |
| --- | --- | --- | --- |
| VAL-1 | FR-2 | The number and order of returned items matches the input batch. | Callers observe one output `Word` per input `Word` in identical sequence order. |
| VAL-2 | FR-3 | Returned items represent the configured target language. | Each returned `Word` is identified as belonging to the target language. |
| VAL-3 | FR-4 | Empty input behaves as a no-op. | `translate([])` returns `[]`. |
| VAL-4 | FR-5 | Unsupported pairs fail before translation work begins. | Translator creation fails explicitly for an unsupported pair. |
| VAL-5 | FR-6 | Translation failures are surfaced through the documented failure contract. | Callers receive `APIError` rather than partial output or silent fallback behavior. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | External translation quality may vary for ambiguous lexical items. | Callers may receive semantically weak but structurally valid translations. | Refine pair-specific translation guidance when target quality requirements become more specific. |
| RISK-2 | Future expansion to additional language pairs may pressure the current contract. | Ad hoc extension could create inconsistent behavior across pairs. | Treat each new pair as an explicit contract update. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should the contract explicitly require hard validation when response cardinality does not match input cardinality? | Open | Module owner to decide in a future spec revision | The current target-state contract requires failure rather than ambiguous output. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Approved | Promoted into explicit requirement | FR-1 |
| RV-2 | A-2 | Approved | Promoted into explicit requirement | FR-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Keep open for future contract hardening review | Next spec revision if stricter cardinality guarantees are required |

### Deferred Work

- D-1: Define the contract for additional language pairs if and when they become in scope.
- D-2: Decide whether response-cardinality validation should be mandated as an explicit contract requirement.
