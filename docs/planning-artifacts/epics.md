---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-create-stories, step-04-final-validation]
inputDocuments:
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md
  - nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md
  - nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md
  - nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md
  - nl_processing/translate_text/docs/prd_translate_text.md
  - nl_processing/translate_text/docs/architecture_translate_text.md
  - nl_processing/translate_word/docs/prd_translate_word.md
  - nl_processing/translate_word/docs/architecture_translate_word.md
---

# nl_processing - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for nl_processing, decomposing the requirements from the PRD and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**Core Package (from shared PRD):**

- CFR1: `core` defines `ExtractedText` — structured output model for text extraction (contains a text field for markdown-formatted extracted text)
- CFR2: `core` defines `WordEntry` — structured output model for word extraction (contains `normalized_form: str` and `word_type: str`)
- CFR3: `core` defines `TranslationResult` — structured output model for word translation (contains `translation: str`, extensible for future fields)
- CFR4: `core` defines `Language` enum with values `NL` (Dutch) and `RU` (Russian), extensible for future languages
- CFR5: All models are importable from `core` by any module — `from nl_processing.core.models import ExtractedText, WordEntry, TranslationResult, Language`
- CFR6: `core` defines `APIError` — typed exception wrapping all upstream OpenAI/LangChain API failures
- CFR7: `core` defines `TargetLanguageNotFoundError` — raised when no text in the target language is detected
- CFR8: `core` defines `UnsupportedImageFormatError` — raised when image format is not supported
- CFR9: All exceptions are importable from `core` — `from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError, UnsupportedImageFormatError`
- CFR10: `core` provides a utility function to load prompt JSON files (in LangChain `ChatPromptTemplate` serialization format) from a given directory path
- CFR11: Each module stores its own prompt JSON files in its own directory (e.g., `nl_processing/extract_text_from_image/prompts/`)
- CFR12: `core` provides a prompt authoring helper script (dev-time only, in `core/scripts/`): the developer writes a temporary Python file with an inline multi-message prompt definition, runs the helper, and it serializes the prompt to JSON in the correct format
- CFR13: The prompt JSON format uses LangChain's `ChatPromptTemplate` native serialization — no custom format
- CFR14: `core` does not define the prompt content — only the loading mechanism and serialization format. Prompt content is a module-level concern

**Shared Module Patterns (from shared PRD):**

- SFR1: Every module uses LangChain's `with_structured_output()` to enforce Pydantic structured output
- SFR2: Every module returns only the requested content — no LLM conversational prefixes, suffixes, or metadata
- SFR3: Every module can be instantiated with zero or minimal arguments and produce a fully functional instance with best-known defaults
- SFR4: Every module uses GPT-5 Mini as the default model
- SFR5: Every module's constructor accepts an optional `model` parameter
- SFR6: Every module uses language-specific prompts written in the target language, stored as JSON files in the module's directory
- SFR7: Every module's interface supports specifying target language(s) via the `Language` enum from `core`
- SFR8: Adding a new language to any module requires only a new prompt JSON file and test cases — no code changes to core logic
- SFR9: Every module wraps upstream API errors as `APIError` from `core`
- SFR10: No raw exceptions from upstream libraries (LangChain, OpenAI) leak to the caller
- SFR11: Module-specific error semantics (what happens when no target-language content is found) are defined in each module's PRD
- SFR12: Every module provides short docstrings on all public interfaces
- SFR13: Every module includes a README or module-level docstring with a quick-start code example
- SFR14: No documentation of internals, prompt engineering, or extension mechanisms

**extract_text_from_image (from module PRD):**

- ETI-FR1: Developer can extract text from an image by providing a file path
- ETI-FR2: Developer can extract text from an image by providing an OpenCV numpy.ndarray
- ETI-FR3: Module extracts only text in the specified target language from the image
- ETI-FR4: Module ignores text in languages other than the target language
- ETI-FR5: Module returns extracted text as a markdown-formatted string
- ETI-FR6: Module preserves the original document's visual structure in markdown (headings, emphasis, line breaks)
- ETI-FR7: Module raises `TargetLanguageNotFoundError` when no text in the target language is detected
- ETI-FR8: Module raises `UnsupportedImageFormatError` when the image format is not supported by the OpenAI API
- ETI-FR9: Module raises `TargetLanguageNotFoundError` when the image contains no text at all
- ETI-FR10: Module includes a utility to generate synthetic test images with known text using OpenCV
- ETI-FR11: Module includes a utility to compare extracted text against ground truth after normalization
- ETI-FR12: Normalization strips whitespace, line breaks, and markdown formatting before comparison
- ETI-FR13: Module includes a utility to run the benchmark suite against a specified model for quality comparison

**extract_words_from_text (from module PRD):**

- EWT-FR1: Developer can extract words from a Markdown-formatted text by providing a string input
- EWT-FR2: Module extracts only words in the specified target language from the text
- EWT-FR3: Module ignores text in languages other than the target language and returns an empty list
- EWT-FR4: Module ignores Markdown formatting and extracts only linguistic content
- EWT-FR5: Module extracts compound expressions and phrasal constructs as single word units
- EWT-FR6: Module normalizes each extracted word according to language-specific rules
- EWT-FR7: Module normalizes Dutch nouns with their article (de/het)
- EWT-FR8: Module normalizes Dutch verbs to infinitive form
- EWT-FR9: Each `WordEntry` contains a normalized form and a word type
- EWT-FR10: Module assigns a flat word type to each extracted word (noun, verb, adjective, preposition, conjunction, proper_noun_person, proper_noun_country, etc.)
- EWT-FR11: Word types are flat strings — no nested structures or hierarchies
- EWT-FR12: Module includes 5 short test cases (1–2 sentences each) with 100% set-based accuracy validation (normalized form + word type)
- EWT-FR13: Module includes a separate performance test for ~100-word text completing in <5 seconds
- EWT-FR14: Each test case covers a variety of word types (nouns with de/het, verbs, adjectives, prepositions, proper nouns, compound expressions)

**translate_text (from module PRD):**

- TT-FR1: Developer can translate Dutch text to Russian by calling a single method with text input
- TT-FR2: Translated text preserves the markdown formatting of the input (headings, bold, italic, lists, paragraph breaks)
- TT-FR3: Translated text reads as natural Russian while staying close to the original meaning and structure
- TT-FR4: Translated text contains only the translation — no conversational prefixes, suffixes, or explanations
- TT-FR5: Developer instantiates the translator by providing source and target language as `Language` enum values (from `core`)
- TT-FR6: Module rejects unsupported language pair combinations with a descriptive exception at instantiation time
- TT-FR7: Empty string input returns empty string (no error)
- TT-FR8: Text with no Dutch content returns empty string (no error)
- TT-FR9: Translation prompt uses few-shot examples stored as JSON to produce natural, human-sounding Russian
- TT-FR10: Translation stays close to original meaning and structure — no creative rewriting, no added content

**translate_word (from module PRD):**

- TW-FR1: Developer can instantiate `WordTranslator` with source and target `Language` enums (from `core`)
- TW-FR2: Developer can call a single translate method with a list of normalized words/phrases and receive a list of `TranslationResult` objects
- TW-FR3: System translates each input word with one-to-one order-preserving mapping
- TW-FR4: System returns `TranslationResult` objects (from `core`) containing a `translation` field
- TW-FR5: System supports Dutch (NL) as source and Russian (RU) as target on initial release
- TW-FR6: Developer can optionally override the default LLM model name via constructor parameter
- TW-FR7: System uses language-specific few-shot prompt JSONs for translation
- TW-FR8: Prompt architecture supports adding new language pairs by adding new prompt JSONs without code changes
- TW-FR9: System returns an empty list when input is an empty list
- TW-FR10: System passes a quality test case of 10 unambiguous Dutch words with 100% exact match against ground truth Russian translations
- TW-FR11: System completes translation of 10 words in less than 1 second

### NonFunctional Requirements

**Core Package (from shared PRD):**

- CNFR1: `core` has no direct user-facing interface — it is internal infrastructure consumed by pipeline modules
- CNFR2: `core` has its own unit tests validating: model serialization, exception hierarchy, prompt loading utility

**Shared Module NFRs (from shared PRD):**

- SNFR0: Extremely loose coupling — modules interact only with `core` (shared package), never with each other. No module may import from another module. The caller (external pipeline code) is responsible for connecting modules.
- SNFR1: Every module uses `langchain` and `langchain-openai` directly for LLM chain construction and execution
- SNFR2: Every module requires only `OPENAI_API_KEY` environment variable for API authentication, managed via Doppler
- SNFR3: Every module is an internal module within `nl_processing` — no PyPI publishing, no standalone packaging
- SNFR4: All public interfaces have type hints
- SNFR5: Every module passes its test suite with 100% accuracy as a prerequisite for any release
- SNFR6: Project-level dependencies: `langchain`, `langchain-openai`, `pydantic`
- SNFR7: All modules depend on `langchain` and `langchain-openai` directly (no abstraction layer)
- SNFR8: Module-specific dependencies (e.g., `opencv-python` for `extract_text_from_image`) are listed in each module's PRD
- SNFR9: Dependencies are managed at project level — no per-module dependency management
- SNFR10: All environment variables and secrets are managed via Doppler CLI — no `.env` files, no `.env.template` files
- SNFR11: Doppler project name: `nl_processing`. Environments: `dev`, `stg`, `prd`
- SNFR12: All commands that require environment variables must be run with `doppler run --` prefix
- SNFR13: Secret values (API keys) must be set by the developer via Doppler — AI agents must not set secret values autonomously
- SNFR14: Non-secret configuration values may be set autonomously via `doppler secrets set`
- SNFR15: All environment variables must be documented in `docs/ENV_VARS.md`
- SNFR16: Environment variables must be set in all three environments (`dev`, `stg`, `prd`) — never in only one
- SNFR17: All test levels (unit, integration, e2e) must pass after every completed task — including integration tests that make real (paid) API calls
- SNFR18: Integration tests are slow and paid but must be run regularly to verify prompt quality and API compatibility
- SNFR19: GitHub Actions CI pipeline runs all tests (including paid integration/e2e) on every PR to `master`

**extract_text_from_image (from module PRD):**

- ETI-NFR1: Each extraction call completes in <= 1 second wall clock time (excluding network latency outside module control)
- ETI-NFR2: Module does not perform unnecessary image processing or conversions that add latency
- ETI-NFR3: Module supports all image formats accepted by the OpenAI Vision API
- ETI-NFR4: `opencv-python` (numpy) for image handling and synthetic test generation

**extract_words_from_text (from module PRD):**

- EWT-NFR1: Each extraction call completes in <5 seconds wall clock time for ~100-word text
- EWT-NFR2: Module does not perform unnecessary text processing that adds latency

**translate_text (from module PRD):**

- TT-NFR1: Translation of ~100-word text completes in < 5 seconds wall clock time
- TT-NFR2: Module instantiation (`TextTranslator` constructor) completes in < 1 second (no API calls at init time)

**translate_word (from module PRD):**

- TW-NFR1: Translation of a batch of 10 words completes in <1 second wall clock time (including network round-trip)
- TW-NFR2: Single LLM call per translate invocation — all words in one batch, not individual calls per word

### Additional Requirements

**From Shared Architecture:**

- No starter template — project already initialized with `pyproject.toml` and `uv`
- No engine abstraction — modules use LangChain directly (no core wrapper)
- Core package = shared models + exceptions + helpers only (flat structure: `models.py`, `exceptions.py`, `prompts.py`, `scripts/prompt_author.py`)
- Prompt JSON format: LangChain `ChatPromptTemplate` native serialization
- Standard module layout: `__init__.py` (empty), `service.py` (public class), `prompts/` dir, `docs/` dir
- Error handling pattern: each module wraps upstream exceptions as `APIError`; module-specific exceptions are domain-level
- Each module instantiates its own `ChatOpenAI` — no shared/singleton LLM client
- Code quality: 200-line file limit, ≤10 code files per module, no silent fallbacks, no `Any`/`cast`/`object` types, no relative imports, empty `__init__.py` files
- `make check` pipeline: ruff format → ruff check → pylint → vulture → jscpd → pytest unit → integration → e2e
- Doppler CLI for all secrets — `doppler run --` prefix for all commands needing env vars
- GitHub Actions CI: runs full `make check` on every PR to `master`, including paid integration/e2e tests
- `.github/workflows/ci.yml` must be created
- Makefile must be updated for `doppler run --` integration
- Test organization: `tests/unit/<module>/`, `tests/integration/<module>/`, `tests/e2e/<module>/`

**From extract_text_from_image Architecture:**

- Uses OpenAI Vision API — image as base64 in prompt messages (HumanMessage with image content parts)
- Two input methods (`extract_from_path`, `extract_from_cv2`) converge to same internal pipeline after base64 encoding
- Image format validation before API call — unsupported formats raise `UnsupportedImageFormatError` immediately
- Synthetic benchmark system (image generator, quality evaluator, model comparison runner) — internal dev tools
- `opencv-python` required for this module only

**From extract_words_from_text Architecture:**

- Flat word-type taxonomy — strings, not enums
- Language-specific normalization entirely via prompt (no hardcoded rules)
- Compound expressions extracted as single `WordEntry` items
- Empty list for non-target language (not an exception)
- Set-based test validation (no ordering/deduplication enforcement)
- No module-specific dependencies beyond core + langchain

**From translate_text Architecture:**

- Prompt-as-product — few-shot examples are the core asset
- Markdown preservation via prompt engineering (not code-based parsing)
- Source + target language constructor (both required, not optional)
- Returns plain `str`, not Pydantic model (structured output used internally only)
- Empty string for edge cases (empty input, non-source language)
- Language pair validation at init time (fail fast)
- Prompt naming: `<source>_<target>.json` (e.g., `nl_ru.json`)
- No module-specific dependencies

**From translate_word Architecture:**

- Single LLM call per batch — all words in one request
- One-to-one order-preserving mapping enforced by Pydantic schema + prompt
- Source + target language constructor (same as translate_text)
- `TranslationResult` — minimal Pydantic model, extensible for future fields
- Empty list for empty input (no API call)
- Prompt naming: `<source>_<target>.json`
- No module-specific dependencies

### FR Coverage Map

**Epic 1 — Core Infrastructure:**
CFR1: Epic 1 — ExtractedText model
CFR2: Epic 1 — WordEntry model
CFR3: Epic 1 — TranslationResult model
CFR4: Epic 1 — Language enum
CFR5: Epic 1 — Model imports from core
CFR6: Epic 1 — APIError exception
CFR7: Epic 1 — TargetLanguageNotFoundError exception
CFR8: Epic 1 — UnsupportedImageFormatError exception
CFR9: Epic 1 — Exception imports from core
CFR10: Epic 1 — Prompt loading utility
CFR11: Epic 1 — Per-module prompt directory convention
CFR12: Epic 1 — Prompt authoring helper script
CFR13: Epic 1 — ChatPromptTemplate native format
CFR14: Epic 1 — Core provides loading only, not content
SFR1-14: Epic 1 — Shared module patterns (validated in each module epic, established in core)

**Epic 2 — extract_text_from_image:**
ETI-FR1: Epic 2 — Extract from file path
ETI-FR2: Epic 2 — Extract from cv2 array
ETI-FR3: Epic 2 — Target language extraction
ETI-FR4: Epic 2 — Ignore non-target languages
ETI-FR5: Epic 2 — Markdown-formatted output
ETI-FR6: Epic 2 — Preserve document structure
ETI-FR7: Epic 2 — TargetLanguageNotFoundError
ETI-FR8: Epic 2 — UnsupportedImageFormatError
ETI-FR9: Epic 2 — TargetLanguageNotFoundError for no text
ETI-FR10: Epic 2 — Synthetic test image generator
ETI-FR11: Epic 2 — Extraction quality evaluator
ETI-FR12: Epic 2 — Normalization for comparison
ETI-FR13: Epic 2 — Model comparison benchmark runner

**Epic 3 — extract_words_from_text:**
EWT-FR1: Epic 3 — Extract words from markdown text
EWT-FR2: Epic 3 — Target language extraction
EWT-FR3: Epic 3 — Empty list for non-target language
EWT-FR4: Epic 3 — Ignore markdown formatting
EWT-FR5: Epic 3 — Compound expressions as single units
EWT-FR6: Epic 3 — Language-specific normalization
EWT-FR7: Epic 3 — Dutch nouns with de/het
EWT-FR8: Epic 3 — Dutch verbs to infinitive
EWT-FR9: Epic 3 — WordEntry with normalized form + type
EWT-FR10: Epic 3 — Flat word type assignment
EWT-FR11: Epic 3 — Flat string types
EWT-FR12: Epic 3 — 5 test cases with set-based validation
EWT-FR13: Epic 3 — Performance test
EWT-FR14: Epic 3 — Diverse word type coverage in tests

**Epic 4 — translate_text:**
TT-FR1: Epic 4 — Translate Dutch to Russian
TT-FR2: Epic 4 — Markdown preservation
TT-FR3: Epic 4 — Natural Russian output
TT-FR4: Epic 4 — Clean output (no LLM chatter)
TT-FR5: Epic 4 — Source + target Language constructor
TT-FR6: Epic 4 — Reject unsupported language pairs
TT-FR7: Epic 4 — Empty string for empty input
TT-FR8: Epic 4 — Empty string for non-Dutch input
TT-FR9: Epic 4 — Few-shot prompt examples
TT-FR10: Epic 4 — Close to original meaning

**Epic 5 — translate_word:**
TW-FR1: Epic 5 — WordTranslator with Language enums
TW-FR2: Epic 5 — Translate word list to TranslationResult list
TW-FR3: Epic 5 — One-to-one order-preserving mapping
TW-FR4: Epic 5 — TranslationResult with translation field
TW-FR5: Epic 5 — Dutch→Russian on initial release
TW-FR6: Epic 5 — Optional model override
TW-FR7: Epic 5 — Few-shot prompt JSONs
TW-FR8: Epic 5 — New language pairs via prompt only
TW-FR9: Epic 5 — Empty list for empty input
TW-FR10: Epic 5 — Quality test (10 words, 100% match)
TW-FR11: Epic 5 — Performance test (<1s for 10 words)

**NFR Coverage:**
CNFR1-2: Epic 1
SNFR0-19: Epic 1 (established), Epics 2-5 (validated per module)
ETI-NFR1-4: Epic 2
EWT-NFR1-2: Epic 3
TT-NFR1-2: Epic 4
TW-NFR1-2: Epic 5

## Epic List

### Epic 1: Core Infrastructure — Shared Foundation
Developer gets a working `core` package (Pydantic models, exceptions, prompt loader, prompt authoring helper), project-level infrastructure (CI pipeline, Makefile with Doppler integration), and test scaffolding. All subsequent modules build on this foundation.
**FRs covered:** CFR1-14, SFR1-14
**NFRs covered:** CNFR1-2, SNFR0-19

### Epic 2: Image Text Extraction — extract_text_from_image
Developer can extract language-specific text from images (file path or cv2 array), receiving clean markdown-formatted output. Includes synthetic benchmarking system for quality validation.
**FRs covered:** ETI-FR1-13
**NFRs covered:** ETI-NFR1-4

### Epic 3: Word Extraction — extract_words_from_text
Developer can extract and normalize words from markdown text, receiving `list[WordEntry]` with normalized forms and flat word types. Language-specific normalization driven entirely by prompts.
**FRs covered:** EWT-FR1-14
**NFRs covered:** EWT-NFR1-2

### Epic 4: Text Translation — translate_text
Developer can translate Dutch text to Russian with markdown formatting preservation and natural, human-sounding output controlled by few-shot prompt examples.
**FRs covered:** TT-FR1-10
**NFRs covered:** TT-NFR1-2

### Epic 5: Word Translation — translate_word
Developer can translate a list of normalized words/phrases in a single batch call, receiving order-preserving `list[TranslationResult]` objects.
**FRs covered:** TW-FR1-11
**NFRs covered:** TW-NFR1-2

---

## Epic 1: Core Infrastructure — Shared Foundation

Developer gets a working `core` package (Pydantic models, exceptions, prompt loader, prompt authoring helper), project-level infrastructure (CI pipeline, Makefile with Doppler integration), and test scaffolding. All subsequent modules build on this foundation.

### Story 1.1: Core Pydantic Models & Language Enum

As an integration developer,
I want importable Pydantic models (`ExtractedText`, `WordEntry`, `TranslationResult`) and a `Language` enum from `core`,
So that all pipeline modules use consistent, typed data contracts.

**Acceptance Criteria:**

**Given** the `core` package exists at `nl_processing/core/`
**When** I import `from nl_processing.core.models import ExtractedText, WordEntry, TranslationResult, Language`
**Then** all four symbols are available and are Pydantic models / enum
**And** `ExtractedText` has a `text: str` field for markdown-formatted extracted text
**And** `WordEntry` has `normalized_form: str` and `word_type: str` fields
**And** `TranslationResult` has a `translation: str` field
**And** `Language` enum has values `NL` and `RU`

**Given** `core/models.py` is created
**When** I run `doppler run -- make check`
**Then** unit tests for model serialization/deserialization pass
**And** ruff, pylint, vulture checks pass
**And** file is under 200 lines

### Story 1.2: Core Exceptions

As an integration developer,
I want typed exceptions (`APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`) importable from `core`,
So that I can handle all pipeline error conditions with clear, specific exception types.

**Acceptance Criteria:**

**Given** the `core` package exists
**When** I import `from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError, UnsupportedImageFormatError`
**Then** all three exceptions are available
**And** `APIError` wraps upstream API failures with a message
**And** `TargetLanguageNotFoundError` and `UnsupportedImageFormatError` are distinct exception types
**And** all exceptions can be raised and caught in standard try/except blocks

**Given** `core/exceptions.py` is created
**When** I run `doppler run -- make check`
**Then** unit tests for exception hierarchy and instantiation pass
**And** ruff, pylint, vulture checks pass

### Story 1.3: Core Prompt Loading Utility

As a module developer,
I want a utility function to load prompt JSON files in LangChain `ChatPromptTemplate` serialization format,
So that each module can load its language-specific prompts from its own directory without custom parsing.

**Acceptance Criteria:**

**Given** a valid prompt JSON file in ChatPromptTemplate format exists at a known path
**When** I call the prompt loading function from `nl_processing.core.prompts` with the file path
**Then** it returns a `ChatPromptTemplate` object ready for chain composition

**Given** a prompt JSON file does not exist at the specified path
**When** I call the prompt loading function
**Then** it raises a clear error (FileNotFoundError or similar)

**Given** `core/prompts.py` is created
**When** I run `doppler run -- make check`
**Then** unit tests for prompt loading (valid file, missing file) pass
**And** ruff, pylint, vulture checks pass

### Story 1.4: Prompt Authoring Helper Script

As a module developer,
I want a dev-time script that serializes inline Python prompt definitions to ChatPromptTemplate JSON files,
So that I can author prompts in Python and export them to the format expected by the prompt loader.

**Acceptance Criteria:**

**Given** a temporary Python file with an inline multi-message prompt definition
**When** I run the prompt authoring helper script (`core/scripts/prompt_author.py`)
**Then** it serializes the prompt to a JSON file in LangChain `ChatPromptTemplate` native format
**And** the output JSON can be loaded by the `core.prompts` loading utility

**Given** the script is in `core/scripts/` (not a Python package)
**When** I inspect the module
**Then** `core/scripts/` is not importable as a Python package (no `__init__.py`)

### Story 1.5: Project Infrastructure — CI Pipeline & Makefile

As a developer,
I want a GitHub Actions CI pipeline and an updated Makefile with Doppler integration,
So that every PR to master runs the full quality gate (`make check`) with secrets injected automatically.

**Acceptance Criteria:**

**Given** a PR is opened against `master`
**When** GitHub Actions triggers
**Then** the CI workflow installs uv, Doppler CLI, and project dependencies
**And** runs `doppler run -- make check` with `DOPPLER_TOKEN` from GitHub secrets
**And** the pipeline fails if any step (ruff, pylint, vulture, jscpd, pytest) fails

**Given** the Makefile is updated
**When** I run `doppler run -- make check` locally
**Then** it executes: ruff format → ruff check → pylint → vulture → jscpd → pytest unit → pytest integration → pytest e2e
**And** all pytest commands run under `doppler run --` for env var injection

**Given** the test directory structure is created
**When** I inspect `tests/`
**Then** directories exist: `tests/unit/core/`, `tests/integration/core/`, and placeholder directories for all 4 modules at all 3 test levels

---

## Epic 2: Image Text Extraction — extract_text_from_image

Developer can extract language-specific text from images (file path or cv2 array), receiving clean markdown-formatted output. Includes synthetic benchmarking system for quality validation.

### Story 2.1: Dutch Extraction Prompt & ImageTextExtractor Service

As an integration developer,
I want to extract Dutch text from images by calling `ImageTextExtractor.extract_from_path()` or `extract_from_cv2()`,
So that I get clean markdown-formatted Dutch text without needing to know anything about LLMs or image processing.

**Acceptance Criteria:**

**Given** `OPENAI_API_KEY` is configured via Doppler
**When** I instantiate `ImageTextExtractor()` with default arguments
**Then** it creates an instance with `language=Language.NL` and `model="gpt-5-mini"`
**And** the constructor accepts optional `language: Language` and `model: str` keyword arguments

**Given** an image file containing Dutch text at a valid path
**When** I call `extractor.extract_from_path("image.png")`
**Then** it returns a markdown-formatted string containing only the Dutch text from the image
**And** the markdown preserves the original document structure (headings, emphasis, line breaks)
**And** text in other languages is excluded from the output

**Given** an OpenCV numpy.ndarray containing Dutch text
**When** I call `extractor.extract_from_cv2(cv2_image)`
**Then** it returns the same markdown-formatted string as `extract_from_path` would for the equivalent image
**And** both methods converge to the same internal base64-encoding + LangChain chain pipeline

**Given** the module uses OpenAI Vision API
**When** the chain is invoked internally
**Then** the image is sent as base64-encoded data in a `HumanMessage` with image content parts
**And** `with_structured_output()` enforces clean output via `ExtractedText` model from `core`

**Given** `service.py` and `prompts/nl.json` are created
**When** I run `doppler run -- make check`
**Then** unit tests (with mocked LangChain chain) pass
**And** ruff, pylint, vulture checks pass
**And** all public methods have type hints and docstrings

### Story 2.2: Error Handling & Format Validation

As an integration developer,
I want clear, typed exceptions for all failure modes (unsupported format, no target language, API errors),
So that my pipeline can handle every error condition with specific except blocks.

**Acceptance Criteria:**

**Given** an image file in a format not supported by the OpenAI Vision API (e.g., `.bmp`)
**When** I call `extractor.extract_from_path("image.bmp")`
**Then** it raises `UnsupportedImageFormatError` from `core` immediately — no API call is made

**Given** an image containing only English text (no Dutch)
**When** I call `extractor.extract_from_path("english_only.png")`
**Then** it raises `TargetLanguageNotFoundError` from `core`

**Given** an image containing no text at all
**When** I call `extractor.extract_from_path("blank.png")`
**Then** it raises `TargetLanguageNotFoundError` from `core`

**Given** the OpenAI API returns an error (rate limit, auth failure, etc.)
**When** the chain invocation fails
**Then** the upstream exception is wrapped as `APIError` from `core`
**And** no raw LangChain or OpenAI exceptions leak to the caller

**Given** error handling is implemented
**When** I run `doppler run -- make check`
**Then** unit tests for each error path (format validation, no target language, no text, API error) pass

### Story 2.3: Synthetic Benchmark System & Integration Tests

As a module developer,
I want synthetic test image generation and extraction quality benchmarking utilities,
So that I can validate extraction accuracy at 100% exact match and compare model quality.

**Acceptance Criteria:**

**Given** the synthetic image generator utility exists within the module
**When** I invoke it with known Dutch text content
**Then** it generates deterministic test images using OpenCV with the specified text rendered on them

**Given** the extraction quality evaluator utility exists
**When** I provide extracted text and ground truth text
**Then** it normalizes both (strips whitespace, line breaks, markdown formatting) and compares them
**And** returns a pass/fail result based on exact match after normalization

**Given** the model comparison runner utility exists
**When** I run it against a specified model
**Then** it executes the full benchmark suite and reports accuracy results per test case

**Given** integration tests are created
**When** I run `doppler run -- pytest tests/integration/extract_text_from_image/`
**Then** real API calls are made with synthetic test images
**And** extraction accuracy is 100% exact match (after normalization) on the synthetic test suite
**And** each extraction call completes in <= 1 second wall clock time

**Given** e2e tests are created
**When** I run `doppler run -- pytest tests/e2e/extract_text_from_image/`
**Then** full extraction scenarios with real-world-like images pass
**And** the module supports all image formats accepted by the OpenAI Vision API

---

## Epic 3: Word Extraction — extract_words_from_text

Developer can extract and normalize words from markdown text, receiving `list[WordEntry]` with normalized forms and flat word types. Language-specific normalization driven entirely by prompts.

### Story 3.1: Dutch Word Extraction Prompt & WordExtractor Service

As an integration developer,
I want to extract and normalize Dutch words from markdown text by calling `WordExtractor.extract()`,
So that I get a flat list of `WordEntry` objects with normalized forms and word types without knowing anything about NLP or normalization rules.

**Acceptance Criteria:**

**Given** `OPENAI_API_KEY` is configured via Doppler
**When** I instantiate `WordExtractor()` with default arguments
**Then** it creates an instance with `language=Language.NL` and `model="gpt-5-mini"`
**And** the constructor accepts optional `language: Language` and `model: str` keyword arguments

**Given** a markdown-formatted Dutch text string
**When** I call `extractor.extract(text)`
**Then** it returns a `list[WordEntry]` where each entry has `normalized_form` and `word_type`
**And** Dutch nouns are normalized with their article (de/het), e.g., "de fiets"
**And** Dutch verbs are normalized to infinitive form, e.g., "lopen"
**And** compound expressions and phrasal constructs are extracted as single `WordEntry` items
**And** word types are flat strings (noun, verb, adjective, preposition, conjunction, proper_noun_person, proper_noun_country, etc.)
**And** markdown formatting is ignored — only linguistic content is extracted

**Given** input text contains no words in the target language (e.g., English-only text)
**When** I call `extractor.extract(text)`
**Then** it returns an empty `list[WordEntry]` — no exception is raised

**Given** the OpenAI API returns an error
**When** the chain invocation fails
**Then** the upstream exception is wrapped as `APIError` from `core`
**And** no raw LangChain or OpenAI exceptions leak to the caller

**Given** `service.py` and `prompts/nl.json` are created
**When** I run `doppler run -- make check`
**Then** unit tests (with mocked LangChain chain) pass for: normal extraction, empty list for non-target language, APIError wrapping
**And** ruff, pylint, vulture checks pass
**And** all public methods have type hints and docstrings

### Story 3.2: Quality Test Cases & Integration Tests

As a module developer,
I want curated test cases validating extraction accuracy and performance,
So that I can verify prompt quality and catch regressions.

**Acceptance Criteria:**

**Given** 5 short test cases (1-2 sentences each) are curated
**When** each test case is processed by `WordExtractor.extract()`
**Then** the output matches the expected word set with 100% accuracy using set comparison (normalized_form + word_type)
**And** each test case covers a variety of word types (nouns with de/het, verbs, adjectives, prepositions, proper nouns, compound expressions)

**Given** a performance test with ~100-word Dutch text exists
**When** the extraction is executed
**Then** it completes in < 5 seconds wall clock time

**Given** integration tests are created
**When** I run `doppler run -- pytest tests/integration/extract_words_from_text/`
**Then** real API calls are made with the 5 curated test cases
**And** set-based accuracy validation passes at 100%

**Given** e2e tests are created
**When** I run `doppler run -- pytest tests/e2e/extract_words_from_text/`
**Then** full extraction from diverse markdown texts passes
**And** all test levels pass in `doppler run -- make check`

---

## Epic 4: Text Translation — translate_text

Developer can translate Dutch text to Russian with markdown formatting preservation and natural, human-sounding output controlled by few-shot prompt examples.

### Story 4.1: Dutch-Russian Translation Prompt & TextTranslator Service

As an integration developer,
I want to translate Dutch text to Russian by calling `TextTranslator.translate()`,
So that I get natural, human-sounding Russian text with markdown formatting preserved.

**Acceptance Criteria:**

**Given** `OPENAI_API_KEY` is configured via Doppler
**When** I instantiate `TextTranslator(source_language=Language.NL, target_language=Language.RU)`
**Then** it creates a working translator instance
**And** the constructor requires `source_language` and `target_language` (both mandatory)
**And** the constructor accepts an optional `model: str` keyword argument (default: `"gpt-5-mini"`)
**And** constructor completes in < 1 second (no API calls at init time)

**Given** an unsupported language pair (e.g., `Language.RU` as source and `Language.NL` as target)
**When** I instantiate `TextTranslator` with that pair
**Then** it raises a descriptive exception at init time — fail fast

**Given** a Dutch markdown-formatted text string
**When** I call `translator.translate(text)`
**Then** it returns a Russian translation as plain `str`
**And** the translation preserves markdown formatting (headings, bold, italic, lists, paragraph breaks)
**And** the output reads as natural Russian, close to original meaning and structure
**And** the output contains only the translation — no conversational prefixes, suffixes, or explanations

**Given** an empty string input
**When** I call `translator.translate("")`
**Then** it returns an empty string — no error

**Given** input text with no Dutch content (e.g., English text)
**When** I call `translator.translate(english_text)`
**Then** it returns an empty string — no error

**Given** the OpenAI API returns an error
**When** the chain invocation fails
**Then** the upstream exception is wrapped as `APIError` from `core`
**And** no raw LangChain or OpenAI exceptions leak to the caller

**Given** `service.py` and `prompts/nl_ru.json` (with few-shot examples) are created
**When** I run `doppler run -- make check`
**Then** unit tests (with mocked chain) pass for: translation, empty input, non-Dutch input, language pair validation, APIError wrapping
**And** ruff, pylint, vulture checks pass
**And** all public methods have type hints and docstrings

### Story 4.2: Translation Quality Validation & Integration Tests

As a module developer,
I want automated quality validation for translation output,
So that I can verify prompt quality, output cleanliness, and catch regressions.

**Acceptance Criteria:**

**Given** integration tests are created with curated Dutch test input
**When** I run `doppler run -- pytest tests/integration/translate_text/`
**Then** real API calls are made
**And** translated output contains no LLM conversational chatter (validated by structured output enforcement)

**Given** a curated Dutch test input containing no proper nouns
**When** it is translated to Russian
**Then** the output contains only Cyrillic characters, punctuation, whitespace, and markdown symbols (validated by regex)

**Given** a curated Dutch markdown test input with headings, bold, italic, and lists
**When** it is translated
**Then** the output preserves the same markdown structure as the input (validated by structural comparison)

**Given** a ~100-word Dutch text
**When** it is translated
**Then** the translation completes in < 5 seconds wall clock time

**Given** e2e tests are created
**When** I run `doppler run -- pytest tests/e2e/translate_text/`
**Then** full translation scenarios with varied markdown content pass
**And** all test levels pass in `doppler run -- make check`

---

## Epic 5: Word Translation — translate_word

Developer can translate a list of normalized words/phrases in a single batch call, receiving order-preserving `list[TranslationResult]` objects.

### Story 5.1: Dutch-Russian Word Translation Prompt & WordTranslator Service

As an integration developer,
I want to translate a list of Dutch words to Russian by calling `WordTranslator.translate()`,
So that I get a one-to-one, order-preserving list of `TranslationResult` objects in a single fast batch call.

**Acceptance Criteria:**

**Given** `OPENAI_API_KEY` is configured via Doppler
**When** I instantiate `WordTranslator(source_language=Language.NL, target_language=Language.RU)`
**Then** it creates a working translator instance
**And** the constructor requires `source_language` and `target_language` (both mandatory)
**And** the constructor accepts an optional `model: str` keyword argument (default: `"gpt-5-mini"`)

**Given** a list of normalized Dutch words/phrases (e.g., `["huis", "lopen", "snel"]`)
**When** I call `translator.translate(words)`
**Then** it returns a `list[TranslationResult]` where each entry has a `translation: str` field
**And** `len(output) == len(input)` — one-to-one mapping
**And** output order matches input order — order-preserving
**And** all words are translated in a single LLM call (not one call per word)

**Given** an empty input list
**When** I call `translator.translate([])`
**Then** it returns an empty list — no error, no API call

**Given** the OpenAI API returns an error
**When** the chain invocation fails
**Then** the upstream exception is wrapped as `APIError` from `core`
**And** no raw LangChain or OpenAI exceptions leak to the caller

**Given** `service.py` and `prompts/nl_ru.json` (with few-shot examples) are created
**When** I run `doppler run -- make check`
**Then** unit tests (with mocked chain) pass for: batch translation, one-to-one mapping, empty input, APIError wrapping
**And** ruff, pylint, vulture checks pass
**And** all public methods have type hints and docstrings

### Story 5.2: Translation Quality Test & Integration Tests

As a module developer,
I want a quality test case and performance validation,
So that I can verify translation accuracy and speed meet targets.

**Acceptance Criteria:**

**Given** a quality test case of 10 unambiguous Dutch words with known Russian translations
**When** I run `doppler run -- pytest tests/integration/translate_word/`
**Then** real API calls are made
**And** all 10 translations match the ground truth exactly — 100% exact match

**Given** a batch of 10 words
**When** translated via `WordTranslator.translate()`
**Then** the translation completes in < 1 second wall clock time (including network round-trip)

**Given** e2e tests are created
**When** I run `doppler run -- pytest tests/e2e/translate_word/`
**Then** full translation scenarios with word lists from realistic pipeline input pass
**And** all test levels pass in `doppler run -- make check`
