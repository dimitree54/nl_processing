---
title: "extract_text_from_image Module Spec"
module_name: "extract_text_from_image"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
---

# Module Spec: extract_text_from_image

## 1. Module Snapshot

### Summary

`extract_text_from_image` provides image-to-text extraction for the `nl_processing` system. It accepts a supported image file path or an OpenCV image array, submits the image for multimodal extraction, and returns markdown-formatted text in the requested target language. The module's supported contract is limited to its public extractor API and typed failure behavior; model-kwargs shaping and multimodal image request construction are delegated to shared `core` utilities.

### System Context

The module sits at the beginning of the text-processing workflow and produces extracted text for downstream processing modules. It relies on `core` for shared language types, prompt loading, image encoding utilities, and common exception classes. Callers use this module as the image-extraction entry point; they do not depend on its internal prompt assets or development helpers.

### In Scope

- Public async image-text extraction through `ImageTextExtractor`.
- Path-based extraction for supported image file formats.
- OpenCV-array extraction for in-memory image data.
- Markdown-formatted extracted text in the requested target language.
- Typed failure behavior for unsupported languages, missing files, unsupported formats, blank extraction results, and upstream invocation/parsing failures.

### Out of Scope

- Video processing or batch orchestration.
- OCR fallback or hybrid OCR-plus-LLM behavior.
- Alternative image input forms such as raw bytes or `PIL.Image`.
- Downstream translation or word-level post-processing.
- Any internal benchmark or prompt-development tooling.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Runtime language support exists only where a prompt asset and validating tests exist. | Needs Review | This defines when a language is considered supported by the module contract. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must provide a public `ImageTextExtractor` class for asynchronous image-text extraction. | Must | This is the supported module entry point for callers. |
| FR-2 | `ImageTextExtractor` construction must accept a target `language` and optional model configuration parameters that shape extraction behavior. | Must | The constructor contract is part of the public API; the exact default model choice is not part of the contract and may change silently. |
| FR-3 | `extract_from_path(path)` must accept a file path, reject unsupported image formats before model invocation, and return extracted markdown text on success. | Must | Input validation must happen before any upstream request. |
| FR-4 | `extract_from_cv2(image)` must accept a `numpy.ndarray` image and return extracted markdown text on success. | Must | Callers may use in-memory OpenCV images without writing files first. |
| FR-5 | If extraction yields empty or whitespace-only text, the module must raise `TargetLanguageNotFoundError`. | Must | Blank extraction is not a successful result. |
| FR-6 | If upstream invocation or response parsing fails, the module must raise `APIError`. | Must | The caller-facing failure contract stays typed and consistent. |
| FR-7 | If the requested language is not supported by bundled runtime assets, construction must raise `UnsupportedLanguageError`. | Must | Unsupported-language detection happens during `ImageTextExtractor` initialization before extraction begins. |
| FR-8 | If a required runtime file is missing, the module must raise `ImageTextFileNotFoundError`. | Must | This includes missing image inputs and any required supported-language assets that disappear unexpectedly at runtime. |

### Rules and Invariants

- BR-1: Both supported extraction entry points must produce the same result semantics: either markdown text or a typed exception.
- BR-2: Unsupported languages must fail during construction before any upstream model call.
- BR-3: Unsupported path formats must fail locally before any upstream model call.
- BR-4: Public extraction behavior is asynchronous.
- BR-5: Successful extraction returns text only; it does not return confidence scores, bounding boxes, or structured OCR metadata.
- BR-6: The implementation may change the default model selection without a contract change when tuning the quality-speed balance.
- BR-7: Shared `core` helpers are the supported source for ChatOpenAI kwarg shaping, image-path encoding, and multimodal image-message construction.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | A single extraction call must stay within the current package latency budget. | Under 20 seconds per call | Matches the package's current validation expectation. |
| NFR-2 | Reliability | Failures must surface as explicit typed exceptions rather than silent fallbacks or partial success values. | No hidden fallback behavior | Aligns with repository fail-fast policy. |
| NFR-3 | Compatibility | The supported public API must remain importable from `nl_processing.extract_text_from_image.service`. | Stable import path | The package does not support `__init__.py` re-export usage. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Notes |
| --- | --- | --- | --- |
| FM-1 | Unsupported file extension for path input | Raise `UnsupportedImageFormatError` before any upstream call | Caller must provide a supported image format. |
| FM-2 | Image contains no target-language text or no text at all | Raise `TargetLanguageNotFoundError` | Blank output is treated as failure. |
| FM-3 | Upstream model invocation or tool-response parsing fails | Raise `APIError` with the original exception chained | Caller may retry or surface the error. |
| FM-4 | Requested language is unsupported because no bundled prompt asset exists for it | Raise `UnsupportedLanguageError` during construction | Unsupported languages are rejected before any extraction call can start. |
| FM-5 | Requested path input does not exist | Raise `ImageTextFileNotFoundError` before extraction succeeds | Missing input files are surfaced as a typed module failure. |

## 3. Public Contract

### Responsibilities and Boundaries

**Responsible For:**

- Accepting supported image inputs through the public extractor API.
- Producing markdown-formatted extracted text in the requested target language.
- Enforcing typed failure behavior for unsupported languages, missing files, unsupported formats, blank results, and upstream failures.

**Not Responsible For:**

- Defining shared exceptions, including `UnsupportedLanguageError`, language enums, or shared models from `core`.
- Providing OCR fallback, post-processing, translation, or workflow orchestration.
- Exposing internal benchmarking or prompt-authoring utilities as supported public API.

### Public Interfaces

| ID | Interface Type | Direction | Counterparty | Contract Summary | Expected Behavior |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python class | Inbound | Callers | `ImageTextExtractor(language, model, reasoning_effort, service_tier, temperature)` | Creates an async extractor configured for the requested language and model options. The exact default model is implementation-defined. |
| IF-2 | Async method | Inbound | Callers | `await extract_from_path(path: str) -> str` | Validates path input, extracts target-language text, and returns markdown text or raises a typed exception. |
| IF-3 | Async method | Inbound | Callers | `await extract_from_cv2(image: numpy.ndarray) -> str` | Accepts an OpenCV image array, extracts target-language text, and returns markdown text or raises a typed exception. |

Documented public support is limited to these interfaces.

### Internal and Non-Contract Notes

- Private benchmark and prompt-development helpers: Internal only; they may move, rename, or disappear without notice.
- Package-local prompt-development files and examples: Internal only; callers must not depend on them.
- `_aextract` and other underscore-prefixed implementation details: Internal only; not a supported interface.

### External Dependencies and Constraints

| ID | Dependency or Constraint | Why It Matters | Behavioral Assumption or Limit | Notes |
| --- | --- | --- | --- | --- |
| EC-1 | `nl_processing.core` shared types, exceptions, prompt helpers, and image helpers | The module's caller-visible contract depends on shared `Language`, `ExtractedText`, `UnsupportedLanguageError`, `build_llm_kwargs(...)`, `encode_image_path(...)`, and `build_image_human_message(...)` | Compatibility depends on `core` preserving these shared contracts | Cross-module coordination is required for breaking changes. |
| EC-2 | Runtime prompt assets for supported languages | Extraction behavior requires a prompt asset for the requested language | Missing bundled prompt assets make the language unsupported at construction time | Language support is asset-backed, not enum-only. |
| EC-3 | Upstream multimodal model service | Extraction success depends on external model availability and response shape | Upstream outages or malformed responses surface as `APIError` | The module does not define fallback behavior. |

### Cross-Module Change References

| Affected Module | Why It Must Change | External Spec or Doc Reference | Ownership Status |
| --- | --- | --- | --- |
| `core` | Shared exception, language, prompt-loading, or extracted-text contract changes can change this module's public behavior | `../../core/docs/module-spec.md` | Exists |

### Compatibility Notes

| ID | Area | Expectation | Impact if Broken | Notes |
| --- | --- | --- | --- | --- |
| COMP-1 | Import path | Callers import from `nl_processing.extract_text_from_image.service` | Consumer code breaks at import time | This is the supported public import path. |
| COMP-2 | Result contract | Successful extraction returns a `str`; failures raise typed exceptions | Callers may mis-handle results or error paths | The module must not switch to mixed success/error payloads without a contract change. |
| COMP-3 | Async API shape | Public extraction methods remain async | Existing callers would need code changes | Any sync alternative would be additive, not replacement. |

## 4. Acceptance and Validation

### Acceptance Criteria

- AC-1: Callers can construct `ImageTextExtractor` through the documented public import path and use it as the supported extraction entry point.
- AC-2: Supported path inputs and OpenCV-array inputs both produce markdown text on successful extraction.
- AC-3: Unsupported path formats fail before upstream invocation.
- AC-4: Blank or whitespace-only extraction results raise `TargetLanguageNotFoundError`.
- AC-5: Upstream invocation or parsing failures raise `APIError`.
- AC-6: Unsupported languages raise `UnsupportedLanguageError` during `ImageTextExtractor` construction.
- AC-7: Missing image files raise `ImageTextFileNotFoundError`.

### High-Level Validation Coverage

| ID | Target | What Must Be True | Observable Evidence or Result |
| --- | --- | --- | --- |
| VAL-1 | FR-1, FR-2, IF-1 | The public class can be constructed through the documented import path with supported configuration inputs | A caller can instantiate the extractor without relying on internal modules or unsupported entry points. |
| VAL-2 | FR-3, IF-2 | Supported path input succeeds and unsupported path input fails locally | Successful calls return markdown text; unsupported formats raise `UnsupportedImageFormatError` before upstream invocation. |
| VAL-3 | FR-4, IF-3 | OpenCV-array input succeeds through the public async method | Successful calls return markdown text from `extract_from_cv2`. |
| VAL-4 | FR-5, FM-2 | Blank extraction is surfaced as a typed failure | Empty or whitespace-only extraction raises `TargetLanguageNotFoundError`. |
| VAL-5 | FR-6, FM-3, NFR-2 | Upstream and parsing failures are not hidden or downgraded | Failures surface as `APIError` rather than fallback results. |
| VAL-6 | FR-7, FM-4 | Unsupported languages fail during construction with a typed module exception | Constructing the extractor with an unsupported language raises `UnsupportedLanguageError` before extraction starts. |
| VAL-7 | FR-8, FM-5 | Missing runtime files are surfaced as typed module failures | Missing image paths raise `ImageTextFileNotFoundError`. |
| VAL-8 | NFR-1 | Extraction stays within the package latency budget | Existing extraction validation includes per-call assertions that successful extraction completes under 20 seconds. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Runtime language support may be assumed from enum presence alone | Callers may expect unsupported languages to work | Keep supported-language expectations explicit, asset-backed, and validated at construction time. |
| RISK-2 | Upstream model behavior may change without a local contract change | Extraction quality or failure patterns may shift unexpectedly | Validate public outcomes regularly against representative inputs. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should unsupported-language construction failures remain prompt-load failures or be normalized into a dedicated module-level exception? | Resolved | Implemented in module spec | Unsupported languages raise `UnsupportedLanguageError` during construction. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |

### Deferred Work

- D-1: Define an explicit supported-language contract if the module expands beyond its current runtime prompt set.
