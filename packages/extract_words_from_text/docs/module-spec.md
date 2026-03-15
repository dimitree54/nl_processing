---
title: "extract_words_from_text Module Spec"
module_name: "extract_words_from_text"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
---

# Module Spec: extract_words_from_text

> This spec describes the module's desired target-state behavior and public contract.
> It defines WHAT the module must do, not HOW it is implemented.
> Document all public interfaces that other modules or end users are expected to use.
> Do not document implementation details such as files, internal classes, helper functions, algorithms, tests, or QA procedures unless the user explicitly requires them.
> Internal-only surfaces do not need full spec coverage, but when they could be mistaken for public API they should be marked as internal or non-contract.

## 1. Module Snapshot

### Summary

`extract_words_from_text` converts caller-provided text into a flat list of normalized lexical items for one declared target language. It accepts plain text and markdown-formatted text and returns `Word` values that downstream modules can translate, filter, or persist. The module owns extraction and normalization only; it does not own language detection, translation, persistence, or OCR.

### System Context

This module sits between text ingestion and downstream vocabulary workflows. Callers choose the target `Language`, provide source text, and receive normalized `Word` objects or a visible failure outcome. The module depends on shared types and exceptions from `nl_processing.core`, and its supported caller contract is intentionally narrow: import `WordExtractor` from `nl_processing.extract_words_from_text.service`, instantiate it, call `extract`, and consume the returned `Word` values.

### In Scope

- The public `WordExtractor` class and its documented constructor options.
- `extract(text)` behavior for plain text and markdown input.
- Normalized `Word` outputs with shared `Language` and `PartOfSpeech` semantics.
- Externally visible empty-result and failure behavior.

### Out of Scope

- OCR or image-to-text input.
- Automatic language detection or target-language selection.
- Translation, persistence, ranking, or downstream deduplication.
- Any guarantee of deterministic ordering or uniqueness in returned results.

### Assumptions

N/A. The contract below does not rely on temporary working assumptions beyond the stated requirements and constraints.

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must support caller import `from nl_processing.extract_words_from_text.service import WordExtractor`, where `WordExtractor(*, language: Language = Language.NL, model: str = "gpt-5-mini", reasoning_effort: str | None = "medium", temperature: float | None = None)` is the supported class interface. | Must | Constructor options and the documented import path are part of the supported caller interface. |
| FR-2 | The module must expose `await WordExtractor.extract(text: str) -> list[Word]`. | Must | `extract` is the supported execution entry point. |
| FR-3 | The module must accept plain text and markdown-formatted text as valid input. | Must | Markdown markup is input syntax, not extraction content. |
| FR-4 | Successful extraction must return only `Word` values whose `normalized_form`, `word_type`, and `language` are populated. | Must | `word_type` must be valid for `PartOfSpeech`. |
| FR-5 | Each successful result must use the extractor instance's configured `language`. | Must | The returned `language` is not inferred from individual words. |
| FR-6 | The module must support single-word and multi-word lexical units when they represent extractable vocabulary items. | Must | Compound expressions may appear as one result item. |
| FR-7 | When no lexical items are found for the configured target language, `extract` must return `[]`. | Must | An empty extraction is a valid outcome. |
| FR-8 | Failures during extraction response acquisition, parsing, or validation must raise `APIError`. | Must | Callers must receive an explicit typed runtime failure. |
| FR-9 | If initialization cannot load valid extraction instructions for the requested language, construction must fail immediately by raising `UnsupportedLanguageError` and must not fall back to another language or another instruction set. | Must | Fail-fast behavior is part of the contract. |

### Rules and Invariants

- BR-1: Every item in a successful result is a `Word`.
- BR-2: `word_type` must validate against `PartOfSpeech`.
- BR-3: All items returned from one extractor instance share the same `language`.
- BR-4: Result ordering is not part of the supported contract.
- BR-5: Result deduplication is not part of the supported contract.
- BR-6: The module must fail fast on unsupported language setup or invalid extraction output; it must not silently degrade, synthesize defaults, or return partial success.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Compatibility | Module runtime compatibility | Python `>=3.12` | Consumers must use the repository-supported Python baseline. |
| NFR-2 | Reliability | Unexpected extraction failures must surface explicitly. | No silent fallback, partial success, or substituted language support | Fail-fast behavior is part of the module contract. |
| NFR-3 | Compatibility | Public outputs must remain based on shared core contracts. | Results use `Word`, `Language`, and `PartOfSpeech` from `nl_processing.core` | Downstream packages consume shared types. |
| NFR-4 | Availability | Supported language behavior requires module-provided extraction instructions to be available at runtime. | Initialization succeeds only when valid instructions exist for the requested language | Missing or invalid instructions are not hidden. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Notes |
| --- | --- | --- | --- |
| FM-1 | Input contains no lexical items in the configured target language. | Return `[]`. | Empty extraction is a valid success case. |
| FM-2 | The requested language lacks valid module-provided extraction instructions. | Constructor fails immediately with `UnsupportedLanguageError` and no fallback language or fallback instruction set is used. | The error is part of the supported initialization contract. |
| FM-3 | The extraction backend fails or returns invalid structured output. | `extract` raises `APIError`. | No partial result is returned. |
| FM-4 | Input includes markdown, mixed formatting, or punctuation. | The module returns lexical content only. | Formatting tokens are not part of the supported result contract. |
| FM-5 | Source text contains multi-word expressions. | The module may return the expression as a single lexical unit. | Callers must accept phrase-level results. |

## 3. Public Contract

### Responsibilities and Boundaries

**Responsible For:**

- Transforming caller-provided text into normalized lexical items for one configured target language.
- Returning shared `Word` DTOs that downstream modules can consume.
- Distinguishing empty extraction from runtime extraction failure.

**Not Responsible For:**

- Detecting the source language or choosing the target language.
- Translating, storing, ranking, reordering, or deduplicating extracted items.
- Exposing or supporting internal extraction schemas or instruction artifacts as public API.

### Public Interfaces

| ID | Interface Type | Direction | Counterparty | Contract Summary | Expected Behavior |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python class | Inbound | Application code and sibling packages | `from nl_processing.extract_words_from_text.service import WordExtractor` and then `WordExtractor(*, language: Language = Language.NL, model: str = "gpt-5-mini", reasoning_effort: str | None = "medium", temperature: float | None = None)` | Creates an extractor bound to one target language and inference profile; construction fails fast with `UnsupportedLanguageError` if required language instructions cannot be loaded. |
| IF-2 | Python async method | Inbound | `WordExtractor` callers | `await extract(text: str) -> list[Word]` | Accepts plain text or markdown and returns normalized lexical items; returns `[]` when no target-language items are found; raises `APIError` on runtime extraction failure. |
| IF-3 | Data contract | Outbound | Callers consuming results | `list[Word]` | Each item contains `normalized_form`, valid `word_type`, and the extractor instance's configured `language`. |

Document all public contract surfaces here, including public classes, methods, functions, commands, endpoints, events, or other supported entry points.

### Internal and Non-Contract Notes

- `WordExtractor` is a supported import from `nl_processing.extract_words_from_text.service`; package-level re-export via `nl_processing.extract_words_from_text` is not part of the contract. The package `__init__.py` is intentionally empty — this is the accepted code style in this repository; consumers must always import from the explicit submodule path.
- Private helper types, temporary response schemas, instruction file structure, and model-integration plumbing are internal only; callers must not import them or depend on them as supported API.
- The absence of ordering or deduplication guarantees is intentional and is not an internal defect or temporary limitation.

### External Dependencies and Constraints

| ID | Dependency or Constraint | Why It Matters | Behavioral Assumption or Limit | Notes |
| --- | --- | --- | --- | --- |
| EC-1 | `nl_processing.core.models` (`Word`, `Language`, `PartOfSpeech`) | Shared types define the constructor and result contract. | Consumer compatibility depends on the core module's type compatibility guarantees. | This module does not redefine those types. |
| EC-2 | `nl_processing.core.exceptions.APIError` | Runtime extraction failures are surfaced through this shared exception type. | Callers that need typed runtime handling must catch `APIError`. | Initialization failures are outside the `APIError` contract. |
| EC-3 | `nl_processing.core.exceptions.UnsupportedLanguageError` | Unsupported-language initialization failure is surfaced through this shared exception type. | Callers that need typed setup-failure handling must catch `UnsupportedLanguageError`. | This applies only to construction-time language setup failures. |
| EC-4 | Module-provided extraction instructions for the selected language | Initialization and extraction semantics depend on those instructions existing and being valid. | Supported language behavior is guaranteed only for languages with valid module-provided instructions. | No fallback language or fallback instruction set is supported. |
| EC-5 | Configured model backend selected via constructor options | Extraction quality and availability depend on the configured backend honoring the documented interface. | The module does not guarantee deterministic ordering or identical lexical choices across backend changes. | Public behavior is defined by the output contract, not by backend internals. |

### Cross-Module Change References

| Affected Module | Why It Must Change | External Spec or Doc Reference | Ownership Status |
| --- | --- | --- | --- |
| N/A | No external module change is required to satisfy this module contract. | N/A | N/A |

### Compatibility Notes

| ID | Area | Expectation | Impact if Broken | Notes |
| --- | --- | --- | --- | --- |
| COMP-1 | Public API surface | Changes to the documented `nl_processing.extract_words_from_text.service.WordExtractor` import path, `WordExtractor` constructor shape, `extract(text)` signature, or return type must be backward-compatible or explicitly versioned. | Callers may fail to import, instantiate, or await the module correctly. | Additive options are compatible; removals or renames are breaking. |
| COMP-2 | Result semantics | Consumers must treat ordering and deduplication as unspecified. | Order-dependent or uniqueness-dependent callers may break. | Consumers should compare by content, not position. |
| COMP-3 | Language support | Adding support for a new language is additive; removing or changing support for an already supported language is breaking. | Existing callers may fail during construction or receive materially different behavior. | Supported behavior depends on valid module-provided instructions. |

## 4. Acceptance and Validation

### Acceptance Criteria

- AC-1: A caller can import `WordExtractor` from `nl_processing.extract_words_from_text.service`, construct it with the documented options, and call `extract` with `str` input.
- AC-2: Plain text and markdown input produce only normalized `Word` results and do not require callers to strip markdown beforehand.
- AC-3: A text with no lexical items in the configured target language yields `[]`.
- AC-4: Runtime extraction acquisition, parsing, or validation failures yield `APIError`.
- AC-5: Requesting a language without valid module-provided extraction instructions causes construction to fail immediately with `UnsupportedLanguageError` and without fallback behavior.
- AC-6: Consumers can treat multi-word lexical expressions as valid single result items.

### High-Level Validation Coverage

| ID | Target | What Must Be True | Observable Evidence or Result |
| --- | --- | --- | --- |
| VAL-1 | FR-1, IF-1 | The documented import path, constructor, and options are usable by callers. | A caller can import `WordExtractor` from `nl_processing.extract_words_from_text.service` and instantiate it with default and explicit options. |
| VAL-2 | FR-2, FR-3, IF-2 | `extract` accepts plain text and markdown-formatted text. | A caller receives a `list[Word]` from both input styles without markdown cleanup as a prerequisite. |
| VAL-3 | FR-4, FR-5, IF-3 | Successful results are valid `Word` values with populated fields and configured language. | Observed output items each contain `normalized_form`, valid `word_type`, and the extractor language. |
| VAL-4 | FR-7 | Empty target-language input is treated as a valid empty extraction. | The observable result is `[]` rather than an exception. |
| VAL-5 | FR-8, EC-2 | Runtime extraction failures surface as typed errors. | The observable failure is `APIError`, not a silent fallback or partial result. |
| VAL-6 | FR-9, EC-3, EC-4 | Unsupported or invalid language setup fails fast during construction. | Construction does not succeed and raises `UnsupportedLanguageError`; no alternate language or alternate instruction set is used. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Changes to language instructions or model backend may materially change normalization outcomes while preserving the same method signatures. | Downstream modules may see behavioral drift in extracted vocabulary. | Review consumer expectations whenever language instructions or backend defaults change. |
| RISK-2 | Callers may incorrectly assume stable ordering or deduplicated output. | Hidden caller coupling can create fragile downstream behavior. | Keep unordered and non-deduplicated semantics explicit in the contract and consumer docs. |

### Open Questions

N/A. No unresolved contract questions remain for this revision.

### Assumption Review Outcomes

N/A. No temporary working assumptions were used in this revision.

### Open Question Resolution

N/A. No open questions were resolved as part of this revision.

### Deferred Work

- D-1: If the module later adds more language-specific setup failure modes, document their exception contracts here explicitly rather than relying on internal prompt-loading details.
