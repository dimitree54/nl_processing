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

`extract_text_from_image` is the vision entrypoint of the `nl_processing` pipeline. It accepts either an image file path or an OpenCV image array, runs an LLM vision extraction flow, and returns markdown-formatted text for the target language. The current shipped prompt set is effectively Dutch-only, and the module wraps image transport, tool-calling output parsing, and basic benchmark helpers.

### System Context

The module sits at the beginning of the text-processing workflow and feeds downstream extract/translate modules. It depends on `core` for shared models, exceptions, and prompt loading, but owns its multimodal message construction, image encoding, and image-format validation.

### In Scope

- Public `ImageTextExtractor` service with async path-based and cv2-based extraction methods.
- Image-to-base64 conversion and supported-format validation for file input.
- Markdown-oriented target-language text extraction via OpenAI/LangChain tool calling.
- Benchmark helpers for synthetic image generation and normalized exact-match comparison.

### Out of Scope

- Video processing or batch extraction orchestration.
- OCR fallback or hybrid OCR+LLM flows.
- Alternative image inputs such as `PIL.Image` or raw bytes.
- Production-ready support for languages without shipped prompt assets.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | `nl.json` remains the only shipped prompt asset unless new language prompts and tests are added together. | Needs Review | The current prompt directory contains only Dutch. |
| A-2 | Normalized exact-match evaluation remains the benchmark gate for prompt/model changes. | Needs Review | Implemented by the local benchmark helpers. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must provide `ImageTextExtractor(language, model, reasoning_effort, service_tier, temperature)` with sensible defaults for async extraction. | Must | Current default model is `gpt-4.1-mini`. |
| FR-2 | `extract_from_path(path)` must validate supported file extensions before invoking the model and must return markdown-formatted extracted text. | Must | Path input is fail-fast on extension errors. |
| FR-3 | `extract_from_cv2(image)` must accept a `numpy.ndarray`, encode it as PNG, and return markdown-formatted extracted text. | Must | cv2 input converges into the same internal extraction path. |
| FR-4 | Whitespace-only or empty extracted text must raise `TargetLanguageNotFoundError`. | Must | Covers blank images and images without target-language text. |
| FR-5 | Upstream invocation or parsing failures must be mapped to `APIError`. | Must | Keeps the failure contract typed for callers. |
| FR-6 | The module must keep local benchmark helpers for synthetic image generation and normalized exact-match evaluation. | Should | Internal development support, not part of the public API. |

### Rules and Invariants

- BR-1: Both public extraction methods must converge into one shared internal extraction pipeline after encoding.
- BR-2: File-path inputs must reject unsupported extensions locally before any API call.
- BR-3: cv2 inputs are always encoded to PNG for model submission.
- BR-4: Prompt selection is driven by `Language.value`, but only languages with shipped prompt assets are actually supported.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | A single extraction call should stay within the current image-extraction latency budget. | Target <10s per call | Existing docs and tests treat this as the QA gate. |
| NFR-2 | Quality | Prompt/model changes should preserve normalized exact-match benchmark behavior on synthetic fixtures. | 100% pass on curated benchmark set | Uses local benchmark helpers. |
| NFR-3 | Dependencies | Keep image handling self-contained inside the module. | `numpy` + `opencv-python` only | No extra image stack is introduced. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Unsupported file extension for path input. | Raise `UnsupportedImageFormatError` before any API call. | Caller chooses a supported input format. |
| FM-2 | Image contains no target-language text or no text at all. | Raise `TargetLanguageNotFoundError`. | Caller can log/skip the item. |
| FM-3 | Prompt, API, or tool-call parsing fails. | Raise `APIError` with the original exception chained. | Caller can retry or surface the failure. |
| FM-4 | Prompt asset for the requested language is missing. | Constructor fails fast during prompt load. | Add the prompt asset and tests before claiming support. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Vision-specific message construction and image transport.
- File-format validation plus path/cv2 encoding helpers.
- Local benchmark helpers for extraction quality regression.

**Does Not Own:**

- Shared DTOs or exception definitions.
- Downstream word extraction or translation logic.
- Any persistent state, cache, or job scheduling.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `await extract_from_path(path: str) -> str` | Validates extension before invoke. |
| IF-2 | Python API | Inbound | Callers | `await extract_from_cv2(image: numpy.ndarray) -> str` | Encodes arrays as PNG. |
| IF-3 | Asset/API | Outbound | Prompt assets + OpenAI | `prompts/<language>.json`, tool schema `ExtractedText`, OpenAI/LangChain chain | Current shipped asset is `nl.json`. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Service instance state | Owned | Target language and pre-built chain. | Runtime only | No persistence across runs. |
| Prompt assets | Owned | Language-specific extraction prompts. | Versioned with the package | Only Dutch is currently shipped. |
| Benchmark helpers | Owned | Synthetic image generation and normalized comparison utilities. | Versioned with the package | Internal tooling. |
| Extracted text payload | Referenced | `core.models.ExtractedText` tool schema. | Shared contract | Used for tool-call parsing. |

### Processing Flow

1. The constructor loads the prompt JSON for the requested language and binds `ExtractedText` as the tool schema on `ChatOpenAI`.
2. `extract_from_path()` validates the extension, reads bytes, and encodes the image to base64 with the correct media type.
3. `extract_from_cv2()` encodes the provided array to PNG base64.
4. The internal extractor submits a multimodal `HumanMessage`, parses the first tool call into `ExtractedText`, and returns `text` or raises the appropriate typed error.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Use LLM vision extraction instead of classical OCR in this module. | Decided | Preserves context-aware extraction and markdown-like structure. | The module depends on multimodal prompting and external API quality. |
| DEC-2 | Offer two public input methods but one internal extraction pipeline. | Decided | Keeps the external API ergonomic without duplicating invoke logic. | Path and cv2 inputs must both stay compatible with `_aextract()`. |
| DEC-3 | Use typed tool-calling output via `ExtractedText`. | Decided | Keeps output clean and machine-parseable. | Malformed tool responses surface as typed API failures. |
| DEC-4 | Keep benchmark tooling inside this package rather than `core`. | Decided | It is specific to image extraction behavior. | Benchmark helpers stay internal and package-local. |

### Consistency Rules

- CR-1: Supported languages require both a prompt asset and tests; changing `Language` alone is insufficient.
- CR-2: Public extraction methods remain async and must not diverge in result semantics.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, DEC-2, CR-2 | QA-1 |
| FR-4 | IF-3, DEC-3 | QA-2 |
| FR-6 | DEC-4, A-2 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: Supported file-path and cv2 inputs both return markdown text through the same observable extraction behavior.
- AC-2: Unsupported path formats fail before the model call, and blank/non-target-language images raise `TargetLanguageNotFoundError`.
- AC-3: Unit, integration, and e2e tests continue covering encoding, parsing, and real-image extraction flows.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest`, `pytest-asyncio`, and existing fixtures under `tests/unit`, `tests/integration`, and `tests/e2e`.
- Treat live API tests as the source of truth for extraction quality.

**Unit:**

- Image encoding helpers, extension validation, constructor behavior, and error wrapping.

**Integration:**

- Synthetic-image extraction accuracy, multilingual negative cases, and latency budgets against the live API.

**Contract:**

- Tool-call parsing into `ExtractedText` and typed error mapping.

**E2E or UI Workflow:**

- Full extraction against shipped image fixtures, including mixed-language and rotated-image scenarios.

**Operational or Non-Functional:**

- Benchmark helper outputs remain available for prompt/model comparison work.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Unit | Path validation and base64 encoding tests | PR CI | Catches format regressions locally. |
| QA-2 | FR-4 | Integration | Live extraction tests for blank/non-target-language scenarios | PR CI / nightly | Depends on API credentials. |
| QA-3 | FR-6 | Unit | Benchmark helper tests for normalized comparison | PR CI | Keeps the benchmark contract stable. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via package check | Protect code quality and packaging. | PR CI | Lint, type, or dead-code failures. |
| SC-2 | Package tests | Preserve extraction behavior and fixtures. | PR CI | Unit/integration/e2e failures. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Real-world extraction quality | Synthetic fixtures do not cover all layouts or image artifacts. | Run the extractor on representative scans/photos and inspect markdown fidelity. | Sample extracted outputs and reviewer notes. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Model defaults and docs drift apart. | Operators may tune the wrong model or performance expectations. | Keep this spec aligned to `service.py` defaults and test budgets. |
| RISK-2 | The module claims benchmark capabilities beyond what the current helper set implements. | Contributors may assume a missing comparison runner exists. | Document benchmark helpers honestly and add a runner only when implemented. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should unsupported languages raise a dedicated module-level error instead of surfacing prompt-load failures? | Open | Project owner to decide before adding more languages | Current behavior is prompt-asset driven. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending future language-support work | Revisit when adding the next prompt asset |

### Deferred Work

- D-1: Support additional image input types only if a downstream workflow needs them.
- D-2: Add a benchmark runner if model-comparison workflows become part of normal development.
