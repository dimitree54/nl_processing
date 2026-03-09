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

## 1. Module Snapshot

### Summary

`translate_text_from_image` is a new multimodal translation module for `nl_processing`. It replaces the current explicit `extract_text_from_image -> translate_text` chain with one LLM call that accepts an image and returns translated markdown text. The first target workflow is Dutch image content translated into Russian while preserving the observable behavior and fail-fast quality bar of the existing two-module pipeline.

### System Context

The module sits beside `extract_text_from_image` and `translate_text` as a developer-facing alternative when callers want translated output directly from an image and do not need the intermediate Dutch text. It depends on `core` for shared language models, prompt loading, and translation-chain setup, and it should consume shared image transport helpers after those helpers are promoted out of `extract_text_from_image`.

### In Scope

- Public async `ImageTextTranslator` service with file-path and cv2 entrypoints.
- Pair-specific multimodal prompt assets for `nl -> ru`.
- One-call image-to-translation flow using OpenAI/LangChain tool calling.
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
| A-1 | `nl -> ru` is the only supported pair for the first release. | Needs Review | Matches the current translation package capability. |
| A-2 | The new module should match the observable contract of the current two-call chain, not expose its internal reasoning or extraction steps. | Needs Review | The user asked for the same behavior in one LLM call. |
| A-3 | Generic image encoding and format validation helpers can be moved into `core` before implementation. | Needs Review | Avoids coupling the new module to `extract_text_from_image` internals. |
| A-4 | Existing image fixtures and translation quality cases can be copied into the new package and maintained locally after the initial seeding pass. | Needs Review | Preserves package-local ownership of tests and prompt assets. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `ImageTextTranslator(source_language, target_language, model, reasoning_effort, service_tier, temperature)` plus async `translate_from_path(path)` and `translate_from_cv2(image)` methods. | Must | Current defaults are `model="gpt-4.1-mini"`, `reasoning_effort=None`, `service_tier="priority"`, `temperature=0`. |
| FR-2 | `translate_from_path(path)` must validate supported image formats before any API call and then encode the image for multimodal submission. | Must | Reuse the current path-validation behavior. |
| FR-3 | `translate_from_cv2(image)` must accept `numpy.ndarray`, encode it as PNG, and converge into the same internal translation pipeline. | Must | Mirrors `extract_text_from_image` semantics. |
| FR-4 | Each translation request must use exactly one LLM invocation and must not call `ImageTextExtractor` or `TextTranslator` at runtime. | Must | The module is a replacement for the chain, not a wrapper around it. |
| FR-5 | The public result must be a plain translated `str` with no conversational prefixes, explanations, or wrapper DTOs. | Must | Matches `translate_text` output semantics. |
| FR-6 | The module must translate only source-language text visible in the image and ignore other languages. | Must | Preserves current chained behavior on mixed-language images. |
| FR-7 | The module must preserve document structure as markdown where the current extraction flow would recover that structure. | Must | Same end-user contract as the chained pipeline. |
| FR-8 | If the image contains no source-language text, the module must raise a typed language-not-found error rather than returning fabricated or fallback output. | Must | Error type requires a shared-contract decision. |
| FR-9 | Unsupported language pairs must be rejected during initialization. | Must | Same fail-fast pattern as `translate_text`. |
| FR-10 | Upstream invoke, tool-call, or parsing failures must be wrapped as `APIError`. | Must | Shared caller contract. |
| FR-11 | The package must ship a prompt-generation script, pair-specific prompt JSON, and local few-shot image examples derived from curated upstream cases. | Must | Prompt assets are a first-class module artifact. |
| FR-12 | The package must own local unit, integration, and e2e tests derived from existing module cases; steady-state test execution must not depend on importing upstream test suites as oracles. | Must | Preserves package isolation. |

### Rules and Invariants

- BR-1: Both public entrypoints must converge into one internal multimodal translation pipeline after encoding.
- BR-2: Adding a language pair requires updating `_SUPPORTED_PAIRS`, prompt assets, local example fixtures, and tests together.
- BR-3: The module must not fall back to the existing two-call chain or to OCR if the single-call prompt fails.
- BR-4: The public API returns only target-language text.
- BR-5: Seeded examples and tests copied from upstream modules become locally owned artifacts in this package.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Single-call image translation must remain interactive for short image inputs. | <10s on the simple synthetic integration fixture | This should also be benchmarked against the current two-call baseline during bring-up. |
| NFR-2 | Quality | The module must pass a curated corpus covering simple, multiline, mixed-language, rotated, vocabulary, and product-box cases. | 100% pass on the reviewed corpus | Mix exact-match and key-term checks where appropriate. |
| NFR-3 | Maintainability | Prompt JSON must remain generated from a checked-in script and local example assets. | No hand-edited JSON prompt files | Follows the current prompt-authoring pattern. |
| NFR-4 | Isolation | Generic image transport code must live in shared infrastructure, not in another package's private implementation. | Shared helper in `core` before implementation | Prevents hidden cross-package coupling. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Unsupported file extension is provided to `translate_from_path`. | Raise `UnsupportedImageFormatError` before any API call. | Caller supplies PNG/JPEG/WebP input. |
| FM-2 | Unsupported language pair is requested. | Raise `ValueError` during initialization. | Add pair support in code, prompts, and tests together. |
| FM-3 | Image contains no source-language text. | Raise a typed language-not-found error. | Caller can log, skip, or surface the failure. |
| FM-4 | Prompt asset is missing or malformed. | Fail fast during service construction. | Regenerate or repair the prompt asset before use. |
| FM-5 | Upstream multimodal call or tool parsing fails. | Raise `APIError` with the original exception chained. | Caller can retry or surface the failure. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- One-call multimodal image-to-translation prompt behavior.
- Public image translation service API and tool-call output parsing.
- Pair-specific few-shot assets and reviewed golden outputs for this module.

**Does Not Own:**

- Intermediate text extraction as a public API.
- OCR fallback or chained-orchestration behavior.
- Generic image transport helpers once those helpers move to `core`.
- Persistence, batch scheduling, or glossary management.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `await translate_from_path(path: str) -> str` | Validates format before model invoke. |
| IF-2 | Python API | Inbound | Callers | `await translate_from_cv2(image: numpy.ndarray) -> str` | Encodes arrays as PNG. |
| IF-3 | Shared helper | Inbound | `core` | `Language`, `APIError`, `build_translation_chain(...)`, shared image transport helper, shared language-not-found error | Shared contract surface. |
| IF-4 | Asset/API | Outbound | Prompt assets + OpenAI | `prompts/nl_ru.json`, `prompts/examples/*`, `_TranslatedImageText` tool schema, LangChain/OpenAI chain | Pair-specific multimodal prompt contract. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Service instance state | Owned | Source language, target language, and pre-built chain. | Runtime only | No persistence. |
| Pair prompt asset | Owned | `nl_ru.json` multimodal translation prompt. | Versioned with the package | Generated from script. |
| Few-shot example images | Owned | Local copies of curated seed images used by the prompt generator. | Versioned with the package | Provenance should be documented. |
| Golden expected outputs | Owned | Reviewed Russian outputs for local tests and prompt examples. | Versioned with the package | Must not be recomputed during normal test runs. |
| Shared image transport helper | Referenced | Base64 encoding and format validation helpers. | Shared dependency | Should live in `core`. |

### Processing Flow

1. The constructor validates `(source_language, target_language)` and loads `prompts/<src>_<tgt>.json` through `core.build_translation_chain(...)`.
2. `translate_from_path()` validates the extension, reads the image, and encodes it to base64 using the shared image helper.
3. `translate_from_cv2()` encodes the provided array as PNG base64 using the same shared helper path.
4. The internal translator submits a multimodal `HumanMessage` with the image payload to the chain.
5. The first tool call is parsed into `_TranslatedImageText`.
6. Empty or whitespace-only tool output raises the shared language-not-found error; otherwise the translated markdown string is returned.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Implement `translate_text_from_image` as a standalone one-call service, not as orchestration over existing services. | Decided | The user explicitly wants one LLM call. | Runtime behavior must not delegate to `extract_text_from_image` or `translate_text`. |
| DEC-2 | Reuse `core.build_translation_chain(...)` for pair validation, prompt loading, and tool binding. | Decided | Keeps pair-handling behavior consistent with `translate_text`. | The new module stays aligned with existing pair-specific prompt conventions. |
| DEC-3 | Promote generic image format validation and base64 encoding helpers into `core` before implementation. | Decided | Avoids cross-package coupling to `extract_text_from_image`. | `extract_text_from_image` should be migrated to the shared helper too. |
| DEC-4 | Seed few-shot examples from existing image-extraction fixtures and translation quality cases, then store them locally in the new package. | Decided | Reuses proven cases without creating permanent hidden dependencies. | The new package owns copied assets and expected outputs after bring-up. |
| DEC-5 | Use reviewed golden outputs in tests instead of calling upstream modules during normal CI. | Decided | Keeps tests deterministic and package-local. | A one-time seeding workflow is needed before the first implementation PR. |
| DEC-6 | Return only translated text from the public API; keep tool schema internal. | Decided | Matches the `translate_text` consumer contract. | Debug-oriented intermediate extraction remains out of scope. |
| DEC-7 | Do not add runtime fallbacks to the existing chain or OCR when the prompt fails. | Decided | Repository policy is fail-fast, no fallbacks. | Quality gaps must be fixed in the prompt/tests, not hidden in code. |

### Consistency Rules

- CR-1: Prompt files are named by pair (`<source>_<target>.json`) and must stay aligned with `_SUPPORTED_PAIRS`.
- CR-2: Example provenance must be documented so contributors know which upstream case each copied fixture came from.
- CR-3: New supported pairs require prompt assets, local seed fixtures, tests, and docs in the same change.
- CR-4: Public usage examples and docs must remain async to match the service contract.

### Seed Corpus Plan

| ID | New Module Asset | Source Material to Reuse | Adaptation for the New Module |
| --- | --- | --- | --- |
| SEED-1 | Simple synthetic image few-shot + integration test | `extract_text_from_image` prompt/example simple Dutch sentence and integration simple-text case | Render the Dutch source image locally and commit a reviewed Russian target string. |
| SEED-2 | Multiline structure-preservation case | `extract_text_from_image` multiline extraction test plus `translate_text` markdown-structure expectations | Use a local synthetic image whose reviewed output checks line breaks and markdown-like structure. |
| SEED-3 | Mixed Dutch/Russian image case | `extract_text_from_image` mixed-language prompt/example and integration test | Keep the same image pattern and commit a Russian translation of the Dutch-only expected output. |
| SEED-4 | English-only negative case | `extract_text_from_image` English-only prompt/examples and integration test | Keep the image locally and teach the prompt to emit empty tool output so the service raises the not-found error. |
| SEED-5 | Vocabulary photo quality case | `extract_text_from_image/tests/e2e/.../dutch_vocabulary.jpg` | Copy the fixture locally and commit a reviewed Russian vocabulary list as the golden output. |
| SEED-6 | Rotated bilingual page quality case | `extract_text_from_image/tests/e2e/.../dutch_vocabulary_rotated.jpg` | Copy the fixture locally and verify only the Dutch column is translated. |
| SEED-7 | Product box quality case | `extract_text_from_image/tests/e2e/.../dutch_product_box.jpg` plus `translate_text` product-box key-term checks | Copy the fixture locally and reuse the key-term/Cyrillic-ratio assertion style for the translated output. |

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-4 | DEC-1, BR-1, IF-1, IF-2 | QA-1 |
| FR-6 | DEC-4, BR-4, SEED-3 | QA-2 |
| FR-8 | IF-3, DEC-7 | QA-3 |
| FR-11 | IF-4, DEC-4, CR-2 | QA-4 |
| NFR-2 | DEC-4, DEC-5, SEED-5, SEED-6, SEED-7 | QA-5 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `ImageTextTranslator` accepts path and cv2 inputs, performs one LLM call, and returns chatter-free Russian text.
- AC-2: Mixed-language images translate only Dutch content, and English-only images raise the shared language-not-found error.
- AC-3: Prompt generator, pair-specific prompt asset, local seed fixtures, and reviewed golden outputs are checked into the new package.
- AC-4: The curated quality corpus passes without runtime fallback to the old chain or OCR.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest`, `pytest-asyncio`, and the same `tests/unit`, `tests/integration`, `tests/e2e` split used by existing modules.
- Seed the first corpus from existing modules, then commit local fixtures and expected outputs so routine CI does not depend on upstream test imports.
- Follow the repo-standard `uv run pytest` flow and live-API integration/e2e pattern.

**Unit:**

- Constructor pair validation.
- Path/cv2 convergence into one internal `_atranslate()` path.
- Unsupported image format short-circuit before any chain call.
- Empty tool output mapping to the shared language-not-found error.
- `APIError` wrapping with preserved exception cause.
- One-call-only behavior using async chain mocks.

**Integration:**

- Simple sentence image translation against a reviewed golden output.
- Multiline or markdown-like structure preservation case.
- Mixed Dutch/Russian image translates Dutch only.
- English-only image raises the language-not-found error.
- Latency gate on the simple synthetic fixture.

**Contract:**

- Prompt asset file exists and is loadable.
- Prompt generator emits the checked-in JSON artifact.
- `_SUPPORTED_PAIRS` stays aligned with prompt filenames.
- Shared image helper contract is used instead of private extraction-package helpers.

**E2E or UI Workflow:**

- Real vocabulary photo translates into the reviewed Russian list.
- Rotated bilingual textbook page translates only the Dutch content.
- Product-box photo preserves the current key-term quality bar using Russian key-term checks and Cyrillic-ratio validation.

**Operational or Non-Functional:**

- Manual benchmark comparison against the current `extract_text_from_image -> translate_text` chain during bring-up.
- Manual review of prompt-example outputs whenever the default model or prompt examples change.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-4 | Unit | Mocked test that both public methods make exactly one chain call and do not delegate to other services | PR CI | Guards the core architectural contract. |
| QA-2 | FR-6 | Integration | Mixed-language image translation test | PR CI / nightly | Derived from the existing extraction mixed-language case. |
| QA-3 | FR-8 | Integration | English-only image raises language-not-found error | PR CI / nightly | Mirrors the chained workflow failure mode. |
| QA-4 | FR-11 | Contract | Prompt-generation and prompt-packaging tests | PR CI | Protects the prompt asset workflow. |
| QA-5 | NFR-2 | E2E | Vocabulary, rotated-page, and product-box quality tests | Nightly / PR CI with credentials | Uses real image fixtures and reviewed outputs. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via `make package-check` | Preserve lint, file-size, type, and unit-test quality. | PR CI | Lint, dead-code, or unit-test failures. |
| SC-2 | Prompt artifact drift test | Ensure generated prompt JSON matches the committed artifact. | PR CI | Generator output differs from checked-in prompt JSON. |
| SC-3 | Package tests | Preserve behavior across unit, integration, and e2e layers. | PR CI / nightly | Any seeded corpus or contract regression. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Translation naturalness on real images | Automated checks cannot fully judge fluency or terminology choices. | Review sample outputs for vocabulary and product-box fixtures after prompt changes. | Reviewer notes and sample outputs. |
| Latency improvement vs the two-call chain | Comparative performance depends on model/network conditions and is noisy for strict CI gating. | Run the same curated corpus through both implementations and compare median latency. | Benchmark notes or saved timing report. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | `core` does not yet expose a precise error for “source language not found in image.” | The new module could inherit misleading exception semantics. | Decide the shared error contract before implementation and refactor extraction if needed. |
| RISK-2 | A single prompt may underperform the specialized two-call pipeline on hard images. | Translation quality could regress on real photos or mixed-language layouts. | Use the seeded corpus and manual review before rollout; expand few-shot coverage where failures appear. |
| RISK-3 | Reusing upstream fixtures without local ownership would create hidden package coupling. | The new package would become fragile and hard to evolve independently. | Copy seed fixtures locally and store reviewed outputs in this package. |
| RISK-4 | Promoting image helpers into `core` requires touching existing extraction code. | The implementation PR will span more than one package. | Make the helper promotion an explicit prerequisite refactor. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should `core` introduce `SourceLanguageNotFoundError` and migrate `extract_text_from_image` away from `TargetLanguageNotFoundError`? | Open | Project owner to decide before implementation | This affects shared failure semantics. |
| OQ-2 | Is beating the current two-call latency baseline a release gate or only a benchmark target? | Open | Project owner to decide during implementation planning | The user asked for one call, but not an explicit latency SLA. |
| OQ-3 | Should the first release expose only `translate_from_path` and `translate_from_cv2`, or also a lower-level `translate_base64` hook for internal tooling? | Open | Keep closed unless an implementation need appears | The current spec keeps the API minimal. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |
| RV-3 | A-3 | Not yet reviewed | Kept as active assumption | A-3 |
| RV-4 | A-4 | Not yet reviewed | Kept as active assumption | A-4 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-5 | OQ-1 | Unresolved | Shared error contract remains open | Decide before implementation starts |
| RV-6 | OQ-2 | Unresolved | Performance gate remains open | Decide during implementation planning |
| RV-7 | OQ-3 | Unresolved | Public API remains minimal in this draft | Revisit only if implementation needs it |

### Deferred Work

- D-1: Add more source/target language pairs after `nl -> ru` is stable with local prompt assets and tests.
- D-2: Add a benchmark utility that compares one-call and two-call pipeline latency and output quality over the seeded corpus.
