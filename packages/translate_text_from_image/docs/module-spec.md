---
title: "translate_text_from_image Module Spec"
module_name: "translate_text_from_image"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
  - "../../extract_text_from_image/docs/module-spec.md"
  - "../../translate_text/docs/module-spec.md"
---

# Module Spec: translate_text_from_image

> This spec describes the module's desired target-state behavior and public contract.
> It defines WHAT the module must do, not HOW it is implemented.
> Document all public interfaces that other modules or end users are expected to use.
> Do not document implementation details such as files, internal classes, helper functions, algorithms, tests, or QA procedures unless the user explicitly requires them.
> Internal-only surfaces do not need full spec coverage, but when they could be mistaken for public API they should be marked as internal or non-contract.

## 1. Module Snapshot

### Summary

`translate_text_from_image` is a multimodal translation module for `nl_processing`. It accepts an image and returns translated markdown text in one LLM call, without requiring callers to manage an intermediate extraction step. The first supported pair is Dutch to Russian. The module must match the observable output quality and fail-fast behavior of the existing two-module pipeline.

### System Context

The module sits beside `extract_text_from_image` and `translate_text` as a developer-facing alternative when callers want translated output directly from an image without needing intermediate Dutch text. It depends on `core` for shared language models, prompt loading, and shared image transport helpers. The module owns its own translation-chain setup. The module is not an orchestrator over existing services; it is a standalone translation entry point.

### In Scope

- Public async `ImageTextTranslator` service with file-path and cv2 entrypoints.
- Pair-specific multimodal prompt assets for `nl -> ru`.
- One-call image-to-translation flow.
- Local few-shot examples and tests seeded from existing extraction and translation modules.
- Quality gates that prove behavior stays aligned with the current chained workflow on a curated corpus.

### Out of Scope

- Runtime fallback to `extract_text_from_image` plus `translate_text`.
- OCR fallback or hybrid OCR+LLM flows.
- Returning intermediate extracted Dutch text from the public API.
- Language pairs other than `nl -> ru`.
- Batch orchestration, caching, streaming, glossary management, or persistence.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | `nl -> ru` is the only supported pair for the first release. | Approved | Matches the current translation package capability. |
| A-2 | The module must match the observable contract of the two-call chain without exposing internal reasoning or extraction steps. | Approved | Single LLM call; no intermediate output exposed. |
| A-3 | Generic image transport and synthetic image helpers are available in `core`. | Resolved | `core` exposes `validate_image_format`, `encode_path_to_base64`, `encode_cv2_to_base64`, and synthetic image helpers used by this module's prompt/tests. |
| A-4 | Existing image fixtures and translation quality cases can be copied into this package and maintained locally after initial seeding. | Approved | Preserves package-local ownership of tests and prompt assets. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `ImageTextTranslator(source_language, target_language, model, reasoning_effort, service_tier, temperature)` with async `translate_from_path(path)` and `translate_from_cv2(image)` methods. | Must | Defaults: `model="gpt-4.1-mini"`, `reasoning_effort=None`, `service_tier="priority"`, `temperature=0`. |
| FR-2 | `translate_from_path(path)` must validate supported image formats before any API call and encode the image for multimodal submission. | Must | Validation must be observable as a typed error before any network call. |
| FR-3 | `translate_from_cv2(image)` must accept `numpy.ndarray`, encode it as PNG, and produce the same translation behavior as `translate_from_path`. | Must | Both entrypoints must converge on identical output semantics. |
| FR-4 | Each translation request must use exactly one LLM invocation and must not delegate to `ImageTextExtractor` or `TextTranslator` at runtime. | Must | The module replaces the chain; it must not wrap it. |
| FR-5 | The public result must be a plain translated `str` with no conversational prefixes, explanations, or wrapper DTOs. | Must | Matches `translate_text` output semantics. |
| FR-6 | The module must translate only source-language text visible in the image and ignore other languages. | Must | Preserves observable behavior on mixed-language images. |
| FR-7 | The module must preserve document structure as markdown where the current extraction flow would recover that structure. | Must | Same end-user contract as the chained pipeline. |
| FR-8 | If the image contains no source-language text, the module must raise `TargetLanguageNotFoundInInputError` rather than returning fabricated or fallback output. | Must | Shared error type from `core`. |
| FR-9 | Unsupported language pairs must be rejected during initialization. | Must | Same fail-fast pattern as `translate_text`. |
| FR-10 | Upstream invoke, tool-call, or parsing failures must surface as `APIError` with the original exception chained. | Must | Shared caller contract. |
| FR-11 | The package must ship a prompt-generation script, pair-specific prompt JSON, and local few-shot image examples derived from curated upstream cases. | Must | Prompt assets are a first-class module artifact; generic synthetic image generation must be reused from `core` rather than reimplemented locally. |
| FR-12 | The package must own local unit, integration, and e2e tests; steady-state test execution must not depend on importing upstream test suites as oracles. | Must | Preserves package isolation. |

### Rules and Invariants

- BR-1: Both public entrypoints must produce identical translation behavior after image encoding.
- BR-2: Adding a language pair requires updating supported pairs, prompt assets, local example fixtures, and tests together.
- BR-3: The module must not fall back to the existing two-call chain or to OCR if the single-call prompt fails.
- BR-4: The public API returns only target-language text.
- BR-5: Seeded examples and tests copied from upstream modules become locally owned artifacts in this package.
- BR-6: Synthetic image generation used by prompt authoring and tests must reuse shared `core` helpers instead of package-local duplicates.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Single-call image translation must remain interactive for short image inputs. | < 10 s on the simple synthetic integration fixture | Should also be benchmarked against the current two-call baseline during bring-up. |
| NFR-2 | Quality | The module must pass a curated corpus covering simple, multiline, mixed-language, rotated, vocabulary, and product-box cases. | 100% pass on the reviewed corpus | Mix exact-match and key-term checks where appropriate. |
| NFR-3 | Maintainability | Prompt JSON must remain generated from a checked-in script and local example assets. | No hand-edited JSON prompt files | Follows the current prompt-authoring pattern. |
| NFR-4 | Isolation | Generic image transport code must live in shared infrastructure, not in another package's private implementation. | Shared helper in `core` before implementation | Prevents hidden cross-package coupling. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Notes |
| --- | --- | --- | --- |
| FM-1 | Unsupported file extension is provided to `translate_from_path`. | Raise `UnsupportedImageFormatError` before any API call. | Caller supplies PNG/JPEG/WebP input. |
| FM-2 | Unsupported language pair is requested at initialization. | Raise `ValueError` during construction. | Add pair support in code, prompts, and tests together. |
| FM-3 | Image contains no source-language text. | Raise `TargetLanguageNotFoundInInputError`. | Shared error type from `core`. |
| FM-4 | Prompt asset is missing or malformed. | Fail fast during service construction. | Regenerate or repair the prompt asset before use. |
| FM-5 | Upstream multimodal call or tool parsing fails. | Raise `APIError` with the original exception chained. | Caller can retry or surface the failure. |

## 3. Public Contract

### Responsibilities and Boundaries

**Responsible For:**

- One-call multimodal image-to-translation behavior.
- Public image translation service API and tool-call output parsing.
- Pair-specific few-shot assets and reviewed golden outputs for this module.

**Not Responsible For:**

- Intermediate text extraction as a public API.
- OCR fallback or chained-orchestration behavior.
- Generic image transport helpers (owned by `core`).
- Persistence, batch scheduling, or glossary management.

### Public Interfaces

| ID | Interface Type | Direction | Counterparty | Contract Summary | Expected Behavior |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python class | Inbound | Callers | `ImageTextTranslator(source_language, target_language, model, reasoning_effort, service_tier, temperature)` | Raises `ValueError` on unsupported pair or missing prompt asset; otherwise ready to translate. |
| IF-2 | Python method | Inbound | Callers | `await translate_from_path(path: str) -> str` | Validates format, raises `UnsupportedImageFormatError` on bad extension before any API call; returns translated markdown `str` on success. |
| IF-3 | Python method | Inbound | Callers | `await translate_from_cv2(image: numpy.ndarray) -> str` | Encodes array as PNG; returns translated markdown `str` on success. Both entrypoints share identical output semantics. |
| IF-4 | Shared library | Inbound | `core` | `Language`, `APIError`, shared image helpers (`validate_image_format`, `encode_path_to_base64`, `encode_cv2_to_base64`, `generate_test_image`, `generate_test_image_data_url`), `TargetLanguageNotFoundInInputError` | Module depends on these `core` contracts; behavioral changes in `core` affect this module. |
| IF-5 | Prompt asset | Internal/Outbound | OpenAI via LangChain | `prompts/nl_ru.json`, `prompts/examples/*`, tool schema | Pair-specific multimodal prompt contract consumed by the translation chain at runtime. |

### Internal and Non-Contract Notes

- `_TranslatedImageText`: Internal tool schema used to parse the LLM tool call. Not a supported public interface; callers must not depend on it directly.
- `prompts/` directory contents: Consumed internally at construction time. The generation script and JSON artifacts are versioned module assets, not public API.

### External Dependencies and Constraints

| ID | Dependency or Constraint | Why It Matters | Behavioral Assumption or Limit | Notes |
| --- | --- | --- | --- | --- |
| EC-1 | `core` shared image helpers | Format validation, base64 encoding, and synthetic image generation are provided by `core`. | `validate_image_format`, `encode_path_to_base64`, `encode_cv2_to_base64`, `generate_test_image`, and `generate_test_image_data_url` must remain stable in `core`. | Changes to these helpers are a breaking risk. |
| EC-2 | `core.TargetLanguageNotFoundInInputError` | The module raises this shared error when no source-language text is found. | Error type and semantics are constrained by `core` contract. | Callers catching this error break on rename or removal. |
| EC-3 | OpenAI multimodal API via LangChain | Translation requires a multimodal-capable model and tool-calling support. | Model must support image input and structured tool responses. | Default model: `gpt-4.1-mini`. |

### Cross-Module Change References

No outstanding cross-module changes are required for the current scope. `core` already provides the shared image transport helpers and error types this module depends on.

### Compatibility Notes

| ID | Area | Expectation | Impact if Broken | Notes |
| --- | --- | --- | --- | --- |
| COMP-1 | Public method signatures | `translate_from_path` and `translate_from_cv2` signatures are stable after first release. | Callers break without a version bump. | Additive changes (new optional params) are acceptable. |
| COMP-2 | Error types | `UnsupportedImageFormatError`, `APIError`, and `TargetLanguageNotFoundInInputError` are part of the public contract. | Callers catching these types break on rename or removal. | These error types are owned by `core` and must be coordinated there. |
| COMP-3 | Output format | Returns plain `str` with no wrapper DTO. | Callers relying on str semantics break if a DTO is introduced. | Any output-type change is a breaking contract change. |

## 4. Acceptance and Validation

### Acceptance Criteria

- AC-1: `ImageTextTranslator` accepts path and cv2 inputs, performs one LLM call per request, and returns chatter-free translated markdown text.
- AC-2: Mixed-language images translate only source-language content; images with no source-language text raise `TargetLanguageNotFoundInInputError`.
- AC-3: Unsupported language pairs and unsupported image formats each produce typed errors before any API call.
- AC-4: Prompt generator script, pair-specific prompt asset, local seed fixtures, and reviewed golden outputs are checked into the package.
- AC-5: The curated quality corpus passes without runtime fallback to the old chain or OCR.
- AC-6: `make check` is fully green on the package.

### High-Level Validation Coverage

| ID | Target | What Must Be True | Observable Evidence or Result |
| --- | --- | --- | --- |
| VAL-1 | FR-4 | Each public entrypoint makes exactly one LLM call and does not invoke `ImageTextExtractor` or `TextTranslator`. | Test confirms one chain invocation per call; no delegation to other services is observable. |
| VAL-2 | FR-5, FR-7 | Translated output is a plain markdown string with no conversational wrapper. | Returned value is `str`; structure matches the markdown structure in the source image. |
| VAL-3 | FR-6 | Mixed-language images yield only target-language translation of source-language content. | Dutch text is translated; non-Dutch text is absent from the result. |
| VAL-4 | FR-8, FM-3 | Images with no source-language text raise `TargetLanguageNotFoundInInputError`. | Error type is `TargetLanguageNotFoundInInputError` from `core`; no fabricated output is returned. |
| VAL-5 | FM-1 | Unsupported file extensions are rejected before any API call. | `UnsupportedImageFormatError` is raised; no network call is observable. |
| VAL-6 | FR-9, FM-2 | Unsupported language pairs are rejected at construction time. | `ValueError` is raised during `ImageTextTranslator(...)` instantiation. |
| VAL-7 | FR-10, FM-5 | LLM or parsing failures surface as `APIError` with original cause chained. | `APIError` is raised; `__cause__` holds the original exception. |
| VAL-8 | NFR-2 | Curated quality corpus passes: simple, multiline, mixed-language, rotated, vocabulary, and product-box cases. | All corpus cases pass with exact-match or key-term assertions on reviewed golden outputs. |
| VAL-9 | NFR-1 | Simple synthetic image translates within the interactive latency target. | Elapsed time is below 10 s on the simple integration fixture. |
| VAL-10 | FR-11, NFR-3 | Prompt generator produces output matching the committed prompt JSON artifact. | Generator output is byte-for-byte identical to the checked-in `nl_ru.json`. |
| VAL-11 | NFR-4, BR-6 | Module reuses `core` image helpers for both runtime transport and synthetic-image generation. | Static import analysis shows prompt authoring/tests use `generate_test_image` or `generate_test_image_data_url` from `core`; no package-local duplicate helper exists. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | A single prompt may underperform the specialized two-call pipeline on hard images. | Translation quality could regress on real photos or mixed-language layouts. | Validate on the seeded corpus before rollout; expand few-shot coverage where failures appear. |
| RISK-2 | Reusing upstream fixtures without local ownership would create hidden package coupling. | The package would become fragile and hard to evolve independently. | Copy seed fixtures locally and store reviewed outputs in this package. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Is beating the current two-call latency baseline a release gate or only a benchmark target? | Open | Project owner to decide during implementation planning | No explicit latency SLA has been set. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Approved | Promoted | FR-1, FR-9 |
| RV-2 | A-2 | Approved | Promoted | FR-4, FR-5, BR-3 |
| RV-3 | A-3 | Resolved | Core image helpers confirmed available | EC-1 |
| RV-4 | A-4 | Approved | Promoted | FR-12, BR-5 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-5 | OQ-1 | Unresolved | Performance gate remains open | Decide during implementation planning |

### Deferred Work

- D-1: Add more source/target language pairs after `nl -> ru` is stable with local prompt assets and tests.
- D-2: Add a benchmark utility that compares one-call and two-call pipeline latency and output quality over the seeded corpus.
