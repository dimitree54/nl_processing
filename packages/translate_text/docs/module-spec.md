---
title: "translate_text Module Spec"
module_name: "translate_text"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
---

# Module Spec: translate_text

## 1. Module Snapshot

### Summary

`translate_text` is the developer-facing text translation module for `nl_processing`. It translates Dutch markdown text into Russian, preserves markdown structure, and returns a plain string rather than a wrapper object. The current implementation supports only the `nl -> ru` pair and relies on a pair-specific prompt asset plus shared chain-building utilities from `core`.

### System Context

The module is used by developers or higher-level workflows that need clean translated text without handling raw LLM output. It depends on `core` for `Language`, `APIError`, and translation-chain setup, and does not own any database, cache, or long-lived state.

### In Scope

- Public async `TextTranslator(source_language, target_language, model)` interface.
- Dutch-to-Russian translation with markdown preservation.
- Fail-fast pair validation and typed upstream error wrapping.
- Pair-specific prompt JSON assets and tests.

### Out of Scope

- Language pairs other than `nl -> ru`.
- Glossaries, terminology management, or code-block-specific translation policy.
- Chunking, streaming, caching, or semantic-quality scoring infrastructure.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | `nl_ru.json` remains the only supported translation prompt until new pairs are implemented in code and tests. | Needs Review | `_SUPPORTED_PAIRS` currently contains only `("nl", "ru")`. |
| A-2 | Returning an empty string for non-source-language input remains an acceptable product contract. | Needs Review | This behavior is tested but depends partly on prompt behavior. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `TextTranslator(source_language, target_language, model)` and `await translate(text: str) -> str`. | Must | Current default model is `gpt-4.1-mini`. |
| FR-2 | The output must preserve markdown structure such as headings, emphasis, lists, and paragraph breaks. | Must | Preserved through prompt behavior, not markdown parsing code. |
| FR-3 | The public result must contain only the translated text and no conversational prefixes or explanations. | Must | Enforced by typed tool-calling output. |
| FR-4 | Unsupported language pairs must be rejected during initialization. | Must | Fail-fast behavior. |
| FR-5 | Blank input must return an empty string without invoking the model. | Must | Explicit short-circuit in code. |
| FR-6 | Upstream invoke or parsing failures must be mapped to `APIError`. | Must | Common failure contract for callers. |

### Rules and Invariants

- BR-1: The public result is always a plain `str`, not a Pydantic wrapper.
- BR-2: The current implementation supports only the `nl -> ru` pair.
- BR-3: Pair validation happens when the service is created, not when translation starts.
- BR-4: The module does not persist translation state or maintain caches.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Text translation should remain interactive for typical short content. | <5s for ~100-word integration test case | Current live-API test gate. |
| NFR-2 | Initialization | Service construction must stay lightweight. | No API calls during init | The constructor only builds the chain. |
| NFR-3 | Quality | Prompt quality must remain reviewable and repeatable. | Pair-specific prompt JSON + human review of examples | Prompt is the main product asset. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Unsupported pair is requested. | Raise `ValueError` at init. | Add pair support in code, prompts, and tests together. |
| FM-2 | Input is blank or whitespace-only. | Return `""` without invoking the chain. | Valid empty-output path. |
| FM-3 | Prompt, API, tool-call, or parsing error occurs. | Raise `APIError`. | Caller can retry or surface the issue. |
| FM-4 | Input contains no Dutch text. | Return `""` under the current prompt contract. | Behavior depends on prompt quality and tests. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Pair-specific text translation prompts.
- Mapping from typed tool output to a plain translated string.
- Developer-facing translation API with clean output semantics.

**Does Not Own:**

- Shared DTOs or prompt-chain helper logic.
- Batch/chunk orchestration, persistence, or caching.
- Specialized policies for code blocks or glossary management.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `await translate(text: str) -> str` | Single public operation. |
| IF-2 | Shared helper | Inbound | `core` | `build_translation_chain(...)`, `Language`, `APIError` | Shared translation infrastructure. |
| IF-3 | Asset/API | Outbound | Prompt assets + OpenAI | `prompts/nl_ru.json`, `_TranslatedText` tool schema, LangChain/OpenAI | Pair-specific asset contract. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Service instance state | Owned | Source language, target language, and pre-built chain. | Runtime only | No persistence. |
| Pair prompt asset | Owned | `nl_ru.json` translation prompt with examples. | Versioned with the package | Main module asset. |
| Typed tool schema | Owned | `_TranslatedText` internal schema for clean output. | Runtime only | Public API still returns `str`. |

### Processing Flow

1. The constructor validates the pair and builds a translation chain through `core.build_translation_chain(...)`.
2. `translate()` returns `""` immediately for blank input.
3. Non-empty text is wrapped in a `HumanMessage` and sent through the async chain.
4. The first tool call is parsed into `_TranslatedText`, and its `text` field is returned or wrapped in `APIError` on failure.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Treat the prompt and few-shot examples as the main product asset. | Decided | Translation quality is dominated by prompt design, not complex code. | Prompt assets need disciplined review and testing. |
| DEC-2 | Preserve markdown through prompt behavior rather than parser/post-processing logic. | Decided | Avoids fragile markdown reconstruction code. | Prompt quality must explicitly cover markdown cases. |
| DEC-3 | Return a plain string instead of a wrapper model. | Decided | The public output is one translated text value. | Tool-calling stays internal only. |
| DEC-4 | Reject unsupported pairs at initialization. | Decided | Fail fast and keep runtime behavior predictable. | New language pairs require code, prompts, and tests together. |

### Consistency Rules

- CR-1: Prompt files are named by pair (`<source>_<target>.json`) and must stay aligned with `_SUPPORTED_PAIRS`.
- CR-2: Public usage examples and docs must remain async to match the real service contract.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, IF-3, DEC-2 | QA-1 |
| FR-3 | IF-3, DEC-3 | QA-2 |
| FR-4 | IF-2, DEC-4, CR-1 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `TextTranslator` supports only the `nl -> ru` pair and rejects unsupported combinations at construction time.
- AC-2: Translation output is chatter-free plain text with preserved markdown structure for supported inputs.
- AC-3: Blank input returns `""`, and upstream failures remain typed as `APIError`.

### Testing Strategy

**Framework and Constraints:**

- Reuse the package-local `pytest` suites and live-API integration/e2e tests.
- Keep prompt quality validation anchored in both automated checks and manual review of example quality.

**Unit:**

- Pair validation, blank-input short-circuit, custom model wiring, and `APIError` wrapping.

**Integration:**

- Live API tests for chatter-free output, Cyrillic-only output on simple cases, markdown preservation, empty-result behavior, and latency.

**Contract:**

- Prompt asset presence and pair-validation behavior.

**E2E or UI Workflow:**

- Full markdown translation scenarios, unsupported-pair init failure, and product-box quality checks.

**Operational or Non-Functional:**

- Manual review of prompt examples for naturalness and closeness to the source text.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Integration | Markdown-preservation integration test | PR CI / nightly | Validates the core UX contract. |
| QA-2 | FR-3 | Integration | Output-cleanliness test for chatter-free translations | PR CI / nightly | Protects public output shape. |
| QA-3 | FR-4 | Unit | Unsupported-pair init test | PR CI | Fail-fast guardrail. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via package check | Preserve package quality and packaging. | PR CI | Lint or dead-code failures. |
| SC-2 | Package tests | Preserve translation behavior and prompt contracts. | PR CI | Unit/integration/e2e failures. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Translation style naturalness | Automated checks do not fully judge fluency or tone. | Review sample translations whenever the prompt examples or model default change. | Reviewer notes and example outputs. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | The spec may overstate empty-output guarantees for non-Dutch input that are partly prompt-driven. | Behavior could drift with prompt/model changes. | Keep the non-Dutch empty-output test in place and review prompt changes carefully. |
| RISK-2 | Docs and code can drift on default model or async usage. | Consumers may copy incorrect usage or expectations. | Treat `service.py` and tests as the source of truth during docs updates. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should markdown code blocks eventually receive a dedicated “preserve as-is” policy? | Open | Product owner to decide if code-block content enters the workflow | Currently out of scope. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending a product decision on code blocks | Revisit if code-block translation becomes a requirement |

### Deferred Work

- D-1: Add more language pairs only together with code updates, prompt assets, and tests.
- D-2: Decide whether code blocks need a specialized translation policy.
