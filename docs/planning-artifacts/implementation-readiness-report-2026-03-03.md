---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
includedFiles:
  prd:
    - docs/planning-artifacts/prd.md
    - nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md
  architecture:
    - docs/planning-artifacts/architecture.md
    - nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md
  epics:
    - docs/planning-artifacts/epics.md
  ux: []
---

# Implementation Readiness Assessment Report

**Date:** 2026-03-03
**Project:** nl_processing

## Step 1: Document Discovery

### PRD Files Found

**Whole Documents:**
- docs/planning-artifacts/prd.md (10285 bytes, Mar 2 23:16:05 2026)
- nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md (7784 bytes, Mar 2 23:16:05 2026)

**Sharded Documents:**
- None found

### Architecture Files Found

**Whole Documents:**
- docs/planning-artifacts/architecture.md (35081 bytes, Mar 2 23:16:05 2026)
- nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md (4341 bytes, Mar 2 23:16:05 2026)

**Sharded Documents:**
- None found

### Epics & Stories Files Found

**Whole Documents:**
- docs/planning-artifacts/epics.md (42359 bytes, Mar 2 23:16:05 2026)

**Sharded Documents:**
- None found

### UX Design Files Found

**Whole Documents:**
- None found

**Sharded Documents:**
- None found

### Additional Related Documents

- nl_processing/extract_text_from_image/docs/product-brief-extract_text_from_image-2026-03-01.md (6197 bytes, Mar 2 23:16:05 2026)

### Issues Found

- WARNING: UX document not found
- Multiple PRD and Architecture documents present across project and module scopes

## PRD Analysis

### Functional Requirements

FR1: `core` defines `ExtractedText` — structured output model for text extraction (contains a text field for markdown-formatted extracted text).
FR2: `core` defines `WordEntry` — structured output model for word extraction (contains `normalized_form: str` and `word_type: str`).
FR3: `core` defines `TranslationResult` — structured output model for word translation (contains `translation: str`, extensible for future fields).
FR4: `core` defines `Language` enum with values `NL` (Dutch) and `RU` (Russian), extensible for future languages.
FR5: All models are importable from `core` by any module — `from nl_processing.core.models import ExtractedText, WordEntry, TranslationResult, Language`.
FR6: `core` defines `APIError` — typed exception wrapping all upstream OpenAI/LangChain API failures. Used by all 4 modules.
FR7: `core` defines `TargetLanguageNotFoundError` — raised when no text in the target language is detected (used by `extract_text_from_image`).
FR8: `core` defines `UnsupportedImageFormatError` — raised when image format is not supported (used by `extract_text_from_image`).
FR9: All exceptions are importable from `core` — `from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError, UnsupportedImageFormatError`.
FR10: `core` provides a utility function to load prompt JSON files (in LangChain `ChatPromptTemplate` serialization format) from a given directory path.
FR11: Each module stores its own prompt JSON files in its own directory (e.g., `nl_processing/extract_text_from_image/prompts/`).
FR12: `core` provides a prompt authoring helper script (dev-time only, in `core/scripts/`): the developer writes a temporary Python file with an inline multi-message prompt definition, runs the helper, and it serializes the prompt to JSON in the correct format.
FR13: The prompt JSON format uses LangChain's `ChatPromptTemplate` native serialization — no custom format.
FR14: `core` does not define the prompt content — only the loading mechanism and serialization format. Prompt content is a module-level concern.
FR15: Every module enforces structured output via LangChain tool calling using Pydantic models (recommended: `bind_tools(...)` + parsing `tool_calls`).
FR16: Every module returns only the requested content — no LLM conversational prefixes, suffixes, or metadata.
FR17: Every module can be instantiated with zero or minimal arguments and produce a fully functional instance with best-known defaults.
FR18: Default model selection is cost-driven: start with GPT-5 Mini as an evaluation baseline, then downgrade to the cheapest model that still passes quality gates (current default target: `gpt-5-nano`).
FR19: Every module's constructor accepts an optional `model` parameter.
FR20: Every module uses language-specific prompts written in the target language, stored as JSON files in the module's directory.
FR21: Every module's interface supports specifying target language(s) via the `Language` enum from `core`.
FR22: Adding a new language to any module requires only a new prompt JSON file and test cases — no code changes to core logic.
FR23: Every module wraps upstream API errors as `APIError` from `core`.
FR24: No raw exceptions from upstream libraries (LangChain, OpenAI) leak to the caller.
FR25: Module-specific error semantics (what happens when no target-language content is found) are defined in each module's PRD.
FR26: Every module provides short docstrings on all public interfaces.
FR27: Every module includes a README or module-level docstring with a quick-start code example.
FR28: No documentation of internals, prompt engineering, or extension mechanisms.
FR29: Developer can extract text from an image by providing a file path.
FR30: Developer can extract text from an image by providing an OpenCV numpy.ndarray.
FR31: Module extracts only text in the specified target language from the image.
FR32: Module ignores text in languages other than the target language.
FR33: Module returns extracted text as a markdown-formatted string.
FR34: Module preserves the original document's visual structure in markdown (headings, emphasis, line breaks).
FR35: Module raises `TargetLanguageNotFoundError` (from `core`) when no text in the target language is detected.
FR36: Module raises `UnsupportedImageFormatError` (from `core`) when the image format is not supported by the OpenAI API.
FR37: Module raises `TargetLanguageNotFoundError` when the image contains no text at all.
FR38: Module includes a utility to generate synthetic test images with known text using OpenCV.
FR39: Module includes a utility to compare extracted text against ground truth after normalization.
FR40: Normalization strips whitespace, line breaks, and markdown formatting before comparison.
FR41: Module includes a utility to run the benchmark suite against a specified model for quality comparison.

Total FRs: 41

### Non-Functional Requirements

NFR1: `core` has no direct user-facing interface — it is internal infrastructure consumed by pipeline modules.
NFR2: `core` has its own unit tests validating: model serialization, exception hierarchy, prompt loading utility.
NFR3: Every module uses `langchain` and `langchain-openai` directly for LLM chain construction and execution.
NFR4: Every module requires only `OPENAI_API_KEY` environment variable for API authentication, managed via Doppler (see Secrets Management section).
NFR5: Every module is an internal module within `nl_processing` — no PyPI publishing, no standalone packaging.
NFR6: All public interfaces have type hints.
NFR7: Every module passes its test suite with 100% accuracy as a prerequisite for any release.
NFR8: Project-level dependencies: `langchain`, `langchain-openai`, `pydantic`.
NFR9: All modules depend on `langchain` and `langchain-openai` directly (no abstraction layer).
NFR10: Module-specific dependencies (e.g., `opencv-python` for `extract_text_from_image`) are listed in each module's PRD.
NFR11: Dependencies are managed at project level — no per-module dependency management.
NFR12: All environment variables and secrets are managed via Doppler CLI — no `.env` files, no `.env.template` files.
NFR13: Doppler project name: `nl_processing`. Environments: `dev`, `stg`, `prd`.
NFR14: All commands that require environment variables must be run with `doppler run --` prefix.
NFR15: Secret values (API keys) must be set by the developer via Doppler — AI agents must not set secret values autonomously.
NFR16: Non-secret configuration values may be set autonomously via `doppler secrets set`.
NFR17: All environment variables must be documented in `docs/ENV_VARS.md`.
NFR18: Environment variables must be set in all three environments (`dev`, `stg`, `prd`) — never in only one.
NFR19: All test levels (unit, integration, e2e) must pass after every completed task — including integration tests that make real (paid) API calls.
NFR20: Integration tests are slow and paid but must be run regularly to verify prompt quality and API compatibility.
NFR21: GitHub Actions CI pipeline runs all tests (including paid integration/e2e) on every PR to `master`.
NFR22: Each extraction call completes in < 10 seconds wall clock time.
NFR23: Module does not perform unnecessary image processing or conversions that add latency.
NFR24: Module supports all image formats accepted by the OpenAI Vision API.
NFR25: `opencv-python` (numpy) for image handling and synthetic test generation.

Total NFRs: 25

### Additional Requirements

- Shared user profile: Integration Developer with zero required LLM/NLP/LangChain/module internals knowledge; integration time in minutes.
- Shared technical success criteria: API errors surfaced as clear typed `APIError`; module usable with zero configuration beyond defaults.
- Business success criteria for shared platform: internal utility modules, success gate is tests passing and default usability.
- Module-specific measurable outcomes include integration time target `< 5 minutes` and extraction latency target `< 10 seconds`.
- Scope statement: no MVP/version split; all features required for single release.
- Initial module language scope: Dutch extraction only.
- Intentional cross-module variation notes: no-target-language semantics, performance targets, and test approaches may differ per module by design.
- Module references identify separate PRDs for all modules (`extract_text_from_image`, `extract_words_from_text`, `translate_text`, `translate_word`).

### PRD Completeness Assessment

- PRD coverage is strong for shared and module-specific FR/NFR definition.
- Requirements are explicit and testable for most behavior, error handling, and performance.
- A UX specification source remains missing from the discovered document set, which reduces readiness evidence for user-facing interaction expectations.

## Epic Coverage Validation

### Coverage Matrix

| FR Number | PRD Requirement | Epic Coverage | Status |
| --------- | --------------- | ------------- | ------ |
| FR1 | `core` defines `ExtractedText` | Epic 1 (CFR1) | Covered |
| FR2 | `core` defines `WordEntry` | Epic 1 (CFR2) | Covered |
| FR3 | `core` defines `TranslationResult` | Epic 1 (CFR3) | Covered |
| FR4 | `core` defines `Language` enum | Epic 1 (CFR4) | Covered |
| FR5 | Core models importable by all modules | Epic 1 (CFR5) | Covered |
| FR6 | `core` defines `APIError` | Epic 1 (CFR6) | Covered |
| FR7 | `core` defines `TargetLanguageNotFoundError` | Epic 1 (CFR7) | Covered |
| FR8 | `core` defines `UnsupportedImageFormatError` | Epic 1 (CFR8) | Covered |
| FR9 | Core exceptions importable by all modules | Epic 1 (CFR9) | Covered |
| FR10 | Prompt JSON loader utility in `core` | Epic 1 (CFR10) | Covered |
| FR11 | Per-module prompt directory storage | Epic 1 (CFR11) | Covered |
| FR12 | Prompt authoring helper script | Epic 1 (CFR12) | Covered |
| FR13 | Native ChatPromptTemplate serialization format | Epic 1 (CFR13) | Covered |
| FR14 | Core manages prompt loading, not prompt content | Epic 1 (CFR14) | Covered |
| FR15 | Structured output enforcement | Epic 1 (SFR1) | Covered |
| FR16 | Clean output without LLM chatter | Epic 1 (SFR2) | Covered |
| FR17 | Zero/minimal-config constructor defaults | Epic 1 (SFR3) | Covered |
| FR18 | Cost-driven default model (`gpt-5-nano` target) | Epic 1 (SFR4) | Covered |
| FR19 | Optional `model` constructor parameter | Epic 1 (SFR5) | Covered |
| FR20 | Language-specific prompt JSON files | Epic 1 (SFR6) | Covered |
| FR21 | Language enum-based interface | Epic 1 (SFR7) | Covered |
| FR22 | Add language via prompt+tests only | Epic 1 (SFR8) | Covered |
| FR23 | Wrap upstream API errors as `APIError` | Epic 1 (SFR9) | Covered |
| FR24 | No raw upstream exceptions leaked | Epic 1 (SFR10) | Covered |
| FR25 | Module-specific no-target-language semantics | Epic 1 (SFR11) | Covered |
| FR26 | Public docstrings on interfaces | Epic 1 (SFR12) | Covered |
| FR27 | README/docstring quick-start examples | Epic 1 (SFR13) | Covered |
| FR28 | No internal/prompt-engineering extension docs | Epic 1 (SFR14) | Covered |
| FR29 | Extract text from file path | Epic 2 (ETI-FR1) | Covered |
| FR30 | Extract text from OpenCV ndarray | Epic 2 (ETI-FR2) | Covered |
| FR31 | Extract only target-language text | Epic 2 (ETI-FR3) | Covered |
| FR32 | Ignore non-target-language text | Epic 2 (ETI-FR4) | Covered |
| FR33 | Return markdown-formatted text | Epic 2 (ETI-FR5) | Covered |
| FR34 | Preserve visual structure in markdown | Epic 2 (ETI-FR6) | Covered |
| FR35 | Raise `TargetLanguageNotFoundError` for no target language | Epic 2 (ETI-FR7) | Covered |
| FR36 | Raise `UnsupportedImageFormatError` for unsupported format | Epic 2 (ETI-FR8) | Covered |
| FR37 | Raise `TargetLanguageNotFoundError` for no text | Epic 2 (ETI-FR9) | Covered |
| FR38 | Synthetic image generation utility | Epic 2 (ETI-FR10) | Covered |
| FR39 | Ground-truth quality comparison utility | Epic 2 (ETI-FR11) | Covered |
| FR40 | Normalization strips whitespace/line breaks/markdown | Epic 2 (ETI-FR12) | Covered |
| FR41 | Benchmark suite runner by model | Epic 2 (ETI-FR13) | Covered |

### Missing Requirements

- No missing FRs detected from the selected PRD set (shared PRD + `extract_text_from_image` PRD).
- Extra FR groups present in epics beyond selected PRD scope: `EWT-FR1-14`, `TT-FR1-10`, `TW-FR1-11` (belong to other module PRDs).

### Coverage Statistics

- Total PRD FRs: 41
- FRs covered in epics: 41
- Coverage percentage: 100%

## UX Alignment Assessment

### UX Document Status

Not Found.

### Alignment Issues

- No direct UX↔PRD or UX↔Architecture alignment validation possible because no UX artifact was provided.

### Warnings

- UX documentation is missing; however, available PRD/Architecture evidence indicates this scope is an internal Python library without web/mobile UI surface, so UX omission appears low risk for current implementation readiness.
- If a user-facing UI is introduced later, a dedicated UX specification will become required for readiness checks.

## Epic Quality Review

### 🔴 Critical Violations

- Epic 1 (`Core Infrastructure — Shared Foundation`) is predominantly framed as a technical milestone (infrastructure/package setup) rather than direct end-user capability, which violates the user-value-first epic rule.

### 🟠 Major Issues

- Story 1.5 combines multiple large concerns (CI pipeline, Doppler integration, full check pipeline, broad test scaffolding), making story scope potentially too large for consistent single-story delivery.
- Some acceptance criteria in infrastructure stories verify tool execution but under-specify explicit user-observable outcomes (for example, integration developer value realization after completion), reducing clarity of delivered value.

### 🟡 Minor Concerns

- Coverage map uses mixed requirement namespaces (`CFR`, `SFR`, module-prefixed FRs), which is valid but increases traceability overhead during audits.
- Epic sequencing is mostly dependency-safe but should explicitly document that Epics 2-5 can be developed in parallel after Epic 1 baseline completion to avoid accidental serial coupling.

### Dependency and Independence Check

- No forward dependencies were found (no Epic N requiring Epic N+1 behavior).
- No explicit circular dependencies found across epics.
- Story-level references to future stories were not detected in acceptance criteria text.

### Recommendations

- Reframe Epic 1 title/outcome in user-value terms (for example, "Developers can integrate standardized language-processing modules with consistent contracts and error handling").
- Split Story 1.5 into smaller independently shippable stories (CI workflow setup, Doppler command integration, test scaffold structure).
- Add explicit "independent completion evidence" notes for large foundational stories to strengthen readiness validation.

## Summary and Recommendations

### Overall Readiness Status

NEEDS WORK

### Critical Issues Requiring Immediate Action

- Epic 1 framing violates the workflow's user-value-first epic standard (currently reads as a technical milestone).
- UX artifact is absent; while low-risk for current library scope, UX traceability is incomplete if any future user-facing surface is introduced.

### Recommended Next Steps

1. Reframe Epic 1 into explicit integration-developer value language and re-validate epic quality gates.
2. Split Story 1.5 into smaller independent stories with direct acceptance-to-value traceability.
3. Add an explicit scope note in planning artifacts confirming "no UI/UX surface" for this release, or add a minimal UX spec if that assumption is not guaranteed.

### Final Note

This assessment identified issues across documentation/discovery, UX alignment, epic quality, and implementation compliance. Address the critical issues before proceeding to further implementation planning. You may still proceed as-is with acknowledged risk if delivery urgency outweighs process conformance.

**Assessor:** OpenCode (BMAD check-implementation-readiness workflow)
**Assessment Date:** 2026-03-03

## Implementation Compliance Validation (Shared Core + extract_text_from_image)

### Non-Compliance Findings (Do Not Fix)

1. Prompt serialization format is custom, not LangChain native `ChatPromptTemplate` serialization.
   - Evidence: `nl_processing/core/prompts.py:12`, `nl_processing/core/prompts.py:35`, `nl_processing/core/scripts/prompt_author.py:48`, `nl_processing/extract_text_from_image/prompts/nl.json:1`
   - Requirement references: Shared PRD `CFR13`; shared architecture "Prompt JSON Format — LangChain ChatPromptTemplate Serialization".

### Compliance Evidence (Validated)

- Core models and exceptions exist and are importable as specified (`models.py`, `exceptions.py`).
- `extract_text_from_image` supports both path and cv2 input flows and raises specified typed exceptions for key error paths.
- Latency QA gate aligns with docs: integration latency test uses `<10s` and passed locally (observed ~3.5s) under `doppler run -- pytest ...`.
- Unit validation executed successfully: `pytest tests/unit/core tests/unit/extract_text_from_image -q` → 55 passed.
