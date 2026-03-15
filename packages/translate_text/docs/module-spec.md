---
title: "translate_text Module Spec"
module_name: "translate_text"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
---

# Module Spec: translate_text

> This spec describes the module's desired target-state behavior and public contract.
> It defines WHAT the module must do, not HOW it is implemented.
> Document all public interfaces that other modules or end users are expected to use.
> Do not document implementation details such as files, internal classes, helper functions, algorithms, tests, or QA procedures unless the user explicitly requires them.
> Internal-only surfaces do not need full spec coverage, but when they could be mistaken for public API they should be marked as internal or non-contract.

## 1. Module Snapshot

### Summary

`translate_text` is a developer-facing translation module within `nl_processing`. It translates Dutch text into Russian, preserves markdown structure in the returned result, and exposes a small async Python API for higher-level workflows that need translated text without raw model-response handling. The module's contract is intentionally narrow and supports only the documented `nl -> ru` workflow.

### System Context

The module sits inside the `nl_processing` package set as the text-translation boundary for callers that already know the source and target languages. It consumes shared language and exception types from `core`, depends on an upstream LLM service for non-empty translation requests, and returns plain translated text to downstream callers. It does not own persistence, caching, or workflow orchestration.

### In Scope

- Public async `TextTranslator` construction and translation calls.
- Dutch-to-Russian text translation.
- Markdown-preserving translated output.
- Empty-result handling for blank and non-Dutch input.
- Typed failure behavior for non-empty translation errors.

### Out of Scope

- Language pairs other than `nl -> ru`.
- Batch translation, chunking, streaming, caching, or persistence.
- Glossary management or terminology enforcement.
- Dedicated code-block translation policy.

### Assumptions

N/A. This spec does not rely on unresolved working assumptions.

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `nl_processing.translate_text.service.TextTranslator(source_language, target_language, model, service_tier)` as its supported public class interface. | Must | Constructor inputs are part of the public contract. |
| FR-2 | `TextTranslator` must support only `Language.NL` as the source language and `Language.RU` as the target language. | Must | Unsupported pairs are outside the supported contract. |
| FR-3 | `await TextTranslator.translate(text: str) -> str` must return Russian translation output as a plain string. | Must | The public result type is not wrapped in a module-specific response object. |
| FR-4 | The returned text must preserve markdown structure such as headings, emphasis, list markers, and paragraph breaks present in the input. | Must | Markdown structure is part of the output contract. |
| FR-5 | The returned text must contain only translation content and no conversational prefixes, explanations, or wrapper text. | Must | Callers receive translation-ready output. |
| FR-6 | Blank or whitespace-only input must return `""`. | Must | Empty input is a supported no-op case. |
| FR-7 | Input that contains no Dutch text must return `""`. | Must | Empty output is the supported no-translation signal for this case. |
| FR-8 | Non-empty translation failures must raise `APIError`. | Must | The module exposes a stable typed failure contract for callers. |

### Rules and Invariants

- BR-1: Public translation output is always a plain `str`.
- BR-2: Unsupported language pairs are rejected when the translator is created.
- BR-3: The module does not own persistent translation state, caches, or stored translation history.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Typical short-form translations should remain interactive for developer-facing usage. | Approximately 5 seconds or less for representative short content of about 100 words. | Keeps higher-level workflows responsive. |
| NFR-2 | Reliability | Failure signaling must remain stable for callers. | Non-empty translation failures are surfaced as `APIError`, with the original failure preserved as the exception cause. | Supports consistent caller error handling. |
| NFR-3 | Statelessness | The module must remain stateless across calls apart from reusable translator configuration. | No durable storage or translation-history ownership inside this module. | Protects module boundaries and caller expectations. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Notes |
| --- | --- | --- | --- |
| FM-1 | An unsupported language pair is requested. | Raise `ValueError` during translator creation. | Caller must select a documented supported pair. |
| FM-2 | Input is blank or whitespace-only. | Return `""`. | This is a supported no-op translation request. |
| FM-3 | Input contains no Dutch text. | Return `""`. | Empty output is the supported no-translation signal. |
| FM-4 | The upstream service is unavailable or returns unusable output for a non-empty request. | Raise `APIError`. | The original failure remains available as the exception cause. |
| FM-5 | Input contains markdown-heavy content. | Return translated text that preserves supported markdown structure. | Structural markdown remains part of the public output contract. |

## 3. Public Contract

### Responsibilities and Boundaries

**Responsible For:**

- Translating Dutch text into Russian through an async Python interface.
- Returning clean translation output as plain text.
- Preserving markdown structure in supported translated output.
- Normalizing non-empty translation failures to `APIError`.

**Not Responsible For:**

- Supporting additional language pairs.
- Batch orchestration, chunking, streaming, caching, or persistence.
- Glossary enforcement or terminology governance.
- Specialized handling rules for fenced code blocks.

### Public Interfaces

| ID | Interface Type | Direction | Counterparty | Contract Summary | Expected Behavior |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python class | Inbound | Developer callers | `nl_processing.translate_text.service.TextTranslator(source_language: Language, target_language: Language, model: str = "gpt-4.1-mini", service_tier: str | None = "priority")` | Creates a reusable translator instance for the supported pair and raises `ValueError` for unsupported pairs. |
| IF-2 | Async method | Inbound | Developer callers | `await TextTranslator.translate(text: str) -> str` | Returns translated Russian text as a plain string, returns `""` for blank or non-Dutch input, and raises `APIError` for non-empty translation failures. |

### Internal and Non-Contract Notes

- Module-private chain builders, prompt configuration, internal schemas, and private constants are internal only and are not part of the supported module contract.
- Any surface not documented in `Public Interfaces` should be treated as non-contract for external callers.

### External Dependencies and Constraints

| ID | Dependency or Constraint | Why It Matters | Behavioral Assumption or Limit | Notes |
| --- | --- | --- | --- | --- |
| EC-1 | `nl_processing.core.models.Language` | The constructor accepts shared language values rather than module-local language types. | Callers must provide supported `Language` enum values. | This module's documented pair is limited to Dutch source and Russian target. |
| EC-2 | Upstream LLM service access | Non-empty translation requests depend on an external model response. | If the upstream service is unavailable or unusable, the module raises `APIError`. | Valid credentials and connectivity are required in caller environments. |
| EC-3 | Caller-selected `model` and `service_tier` values | Translation quality and latency can vary with the chosen upstream configuration. | The selected upstream option must still support the module's translated-text contract. | This spec fixes the output contract, not identical quality across all upstream options. |

### Cross-Module Change References

N/A. This spec does not require contract changes in other module specs.

### Compatibility Notes

| ID | Area | Expectation | Impact if Broken | Notes |
| --- | --- | --- | --- | --- |
| COMP-1 | Python API shape | The supported API remains async and returns plain `str` results. | Callers would need code changes if the return type or async contract changed. | Applies to `TextTranslator` construction and `translate()`. |
| COMP-2 | Pair validation timing | Unsupported pairs continue to fail during translator creation. | Callers relying on fail-fast setup would break if validation moved later. | Pair expansion is additive only when explicitly documented. |
| COMP-3 | Empty-result semantics | Blank and non-Dutch input continue to use `""` as the no-translation result. | Callers that interpret empty output as "no translation produced" would see behavioral change. | This behavior is part of the supported contract. |

## 4. Acceptance and Validation

### Acceptance Criteria

- AC-1: A caller can create `TextTranslator` only for `Language.NL -> Language.RU`; unsupported pairs fail immediately with `ValueError`.
- AC-2: Dutch markdown input returns Russian text as a plain string with headings, list markers, emphasis, and paragraph breaks preserved where present.
- AC-3: The returned text contains only translation content and no conversational prefixes, explanations, or wrapper text.
- AC-4: Blank or non-Dutch input returns `""`.
- AC-5: Non-empty translation failures surface as `APIError`.

### High-Level Validation Coverage

| ID | Target | What Must Be True | Observable Evidence or Result |
| --- | --- | --- | --- |
| VAL-1 | FR-1, FR-2, IF-1 | The constructor exposes the documented parameters and enforces the supported pair boundary. | Supported constructor calls succeed; unsupported pairs fail before translation starts. |
| VAL-2 | FR-3, FR-4, FR-5, IF-2 | Translation output remains plain-text, markdown-preserving, and free of conversational chatter. | Returned strings preserve expected markdown markers and contain only translated content. |
| VAL-3 | FR-6, FR-7, FM-2, FM-3 | No-translation scenarios produce the documented empty-string result. | Caller receives `""` for blank or non-Dutch input. |
| VAL-4 | FR-8, FM-4, EC-2 | Upstream failures are normalized to the module's public error contract. | Caller receives `APIError`, with the originating failure retained as the cause. |
| VAL-5 | NFR-1 | Typical short translations remain interactive. | Representative short-form translations complete within the stated latency target. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Translation quality and latency vary by caller-selected model and upstream service behavior. | Callers may see different fluency or responsiveness while still using the same API contract. | Validate the representative models used in production-facing workflows. |
| RISK-2 | The empty-string contract for non-Dutch input depends on continued upstream translation behavior. | Callers relying on `""` as a no-translation signal may see regressions if upstream behavior drifts. | Treat this behavior as a required contract and revalidate it when prompts or default model choices change. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should fenced code blocks remain unchanged rather than being translated when they appear inside markdown input? | Open | Product owner follow-up if code-bearing markdown enters scope. | The current module contract requires markdown structure preservation but does not define a code-block-specific policy. |

### Assumption Review Outcomes

N/A. This spec does not include unresolved assumptions that require review outcomes.

### Open Question Resolution

N/A. No open questions were resolved in this revision.

### Deferred Work

- D-1: Add new language pairs only through explicit contract expansion with corresponding acceptance and validation updates.
- D-2: Define a dedicated code-block policy only if code-bearing markdown becomes an in-scope workflow.
