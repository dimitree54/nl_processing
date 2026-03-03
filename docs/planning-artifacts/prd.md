---
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - nl_processing (Shared)

**Author:** Dima
**Date:** 2026-03-01

> This document defines requirements shared across all `nl_processing` modules, including the `core` package that provides common infrastructure. Module-specific requirements (API surface, domain logic, success criteria) are defined in each module's dedicated PRD.

## Executive Summary

`nl_processing` is a set of composable internal Python modules for LLM-powered language processing. All modules share a common `core` package (`nl_processing/core/`) that provides: public interface Pydantic models, shared exceptions, and prompt loading utilities. Each module uses LangChain and langchain-openai directly to build and execute its own chains. This shared PRD captures the cross-cutting requirements and the `core` package specification.

## Project Classification

- **Project Type:** Developer tool (internal Python modules)
- **Domain:** Scientific (ML-AI powered linguistic processing)
- **Complexity:** Medium (quality validation and benchmarking required, no regulatory requirements)
- **Project Context:** Greenfield

## Shared User Profile

All modules target the same user:

**The Integration Developer** — a Python developer building text processing pipelines. No LLM, NLP, LangChain, or module internals knowledge required. Expects: import, instantiate with defaults, call one method, get results. Total integration time: minutes.

## Shared Success Criteria

### User Success (All Modules)

- Developer integrates any module in minutes using only the module's README/docstring
- Zero knowledge of LLMs, LangChain, NLP, or module internals required
- Clear, typed exceptions make error handling straightforward in pipeline code

### Technical Success (All Modules)

- Module-specific test suite passes with 100% accuracy — primary quality gate
- API errors from OpenAI surfaced as clear, typed `APIError` from `core`
- Module is usable with zero configuration beyond defaults

### Business Success

N/A — internal utility modules. Success is binary: all tests pass, module works with default configuration.

---

## Core Package — `nl_processing/core/`

The `core` package is the shared infrastructure layer. It is not a user-facing module — it is consumed only by the 4 pipeline modules internally.

### Core Functional Requirements

#### Pydantic Interface Models

Only Pydantic models that form public module interfaces (input/output contracts) are defined in `core`. Internal models used within a module (e.g., intermediate schemas for LangChain chains) remain in the module. This centralizes public schema definitions and ensures cross-module consistency.

- CFR1: `core` defines `ExtractedText` — structured output model for text extraction (contains a text field for markdown-formatted extracted text)
- CFR2: `core` defines `WordEntry` — structured output model for word extraction (contains `normalized_form: str` and `word_type: str`)
- CFR3: `core` defines `TranslationResult` — structured output model for word translation (contains `translation: str`, extensible for future fields)
- CFR4: `core` defines `Language` enum with values `NL` (Dutch) and `RU` (Russian), extensible for future languages
- CFR5: All models are importable from `core` by any module — `from nl_processing.core.models import ExtractedText, WordEntry, TranslationResult, Language`

#### Exceptions

- CFR6: `core` defines `APIError` — typed exception wrapping all upstream OpenAI/LangChain API failures. Used by all 4 modules.
- CFR7: `core` defines `TargetLanguageNotFoundError` — raised when no text in the target language is detected (used by `extract_text_from_image`)
- CFR8: `core` defines `UnsupportedImageFormatError` — raised when image format is not supported (used by `extract_text_from_image`)
- CFR9: All exceptions are importable from `core` — `from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError, UnsupportedImageFormatError`

#### Prompt Management

- CFR10: `core` provides a utility function to load prompt JSON files (in LangChain `ChatPromptTemplate` serialization format) from a given directory path
- CFR11: Each module stores its own prompt JSON files in its own directory (e.g., `nl_processing/extract_text_from_image/prompts/`)
- CFR12: `core` provides a prompt authoring helper script (dev-time only, in `core/scripts/`): the developer writes a temporary Python file with an inline multi-message prompt definition, runs the helper, and it serializes the prompt to JSON in the correct format
- CFR13: The prompt JSON format uses LangChain's `ChatPromptTemplate` native serialization — no custom format
  - Implementation note: current `core.prompts.load_prompt()` is temporarily implemented against a simplified `{ "messages": [[role, template], ...] }` shape and is non-compliant with CFR13. A follow-up sprint will migrate prompt saving/loading to LangChain native serialization.
- CFR14: `core` does not define the prompt content — only the loading mechanism and serialization format. Prompt content is a module-level concern

### Core Non-Functional Requirements

- CNFR1: `core` has no direct user-facing interface — it is internal infrastructure consumed by pipeline modules
- CNFR2: `core` has its own unit tests validating: model serialization, exception hierarchy, prompt loading utility

---

## Shared Functional Requirements (All Pipeline Modules)

### Structured Output

- SFR1: Every module enforces structured output via LangChain tool calling using Pydantic models (recommended: `bind_tools([...], tool_choice=...)` + parsing `tool_calls`). `with_structured_output()` is allowed but not the preferred standard.
- SFR2: Every module returns only the requested content — no LLM conversational prefixes, suffixes, or metadata

### Configuration

- SFR3: Every module can be instantiated with zero or minimal arguments and produce a fully functional instance with best-known defaults
- SFR4: Default model selection is cost-driven: start with GPT-5 Mini as a baseline and then downgrade to the cheapest model that still passes the module's quality gates (benchmarks/tests) without loss of output quality. Current default target for modules is `gpt-5-nano` (overrideable per module).
- SFR5: Every module's constructor accepts an optional `model` parameter

### Language Support

- SFR6: Every module uses language-specific prompts written in the target language, stored as JSON files in the module's directory
- SFR7: Every module's interface supports specifying target language(s) via the `Language` enum from `core`
- SFR8: Adding a new language to any module requires only a new prompt JSON file and test cases — no code changes to core logic

### Error Handling

- SFR9: Every module wraps upstream API errors as `APIError` from `core`
- SFR10: No raw exceptions from upstream libraries (LangChain, OpenAI) leak to the caller
- SFR11: Module-specific error semantics (what happens when no target-language content is found) are defined in each module's PRD

### Documentation

- SFR12: Every module provides short docstrings on all public interfaces
- SFR13: Every module includes a README or module-level docstring with a quick-start code example
- SFR14: No documentation of internals, prompt engineering, or extension mechanisms

## Shared Non-Functional Requirements (All Pipeline Modules)

### Integration

- SNFR1: Every module uses `langchain` and `langchain-openai` directly for LLM chain construction and execution
- SNFR2: Every module requires only `OPENAI_API_KEY` environment variable for API authentication, managed via Doppler (see Secrets Management section)
- SNFR3: Every module is an internal module within `nl_processing` — no PyPI publishing, no standalone packaging

### Code Quality

- SNFR4: All public interfaces have type hints
- SNFR5: Every module passes its test suite with 100% accuracy as a prerequisite for any release

### Dependencies

- SNFR6: Project-level dependencies: `langchain`, `langchain-openai`, `pydantic`
- SNFR7: All modules depend on `langchain` and `langchain-openai` directly (no abstraction layer)
- SNFR8: Module-specific dependencies (e.g., `opencv-python` for `extract_text_from_image`) are listed in each module's PRD
- SNFR9: Dependencies are managed at project level — no per-module dependency management

### Secrets Management

- SNFR10: All environment variables and secrets are managed via Doppler CLI — no `.env` files, no `.env.template` files
- SNFR11: Doppler project name: `nl_processing`. Environments: `dev`, `stg`, `prd`
- SNFR12: All commands that require environment variables must be run with `doppler run --` prefix
- SNFR13: Secret values (API keys) must be set by the developer via Doppler — AI agents must not set secret values autonomously
- SNFR14: Non-secret configuration values may be set autonomously via `doppler secrets set`
- SNFR15: All environment variables must be documented in `docs/ENV_VARS.md`
- SNFR16: Environment variables must be set in all three environments (`dev`, `stg`, `prd`) — never in only one

### Testing Policy

- SNFR17: All test levels (unit, integration, e2e) must pass after every completed task — including integration tests that make real (paid) API calls
- SNFR18: Integration tests are slow and paid but must be run regularly to verify prompt quality and API compatibility
- SNFR19: GitHub Actions CI pipeline runs all tests (including paid integration/e2e) on every PR to `master`

---

## Cross-Module Consistency Notes

The following differences between modules are intentional design decisions, not inconsistencies:

### Error semantics for "no content in target language"

Each module defines its own semantics for handling input that contains no content in the target language. This is appropriate because each module has different return types and usage contexts. See individual module PRDs for specifics.

### Performance targets

Performance targets vary by module based on processing characteristics (vision API calls vs text processing vs batch translation). See individual module PRDs for specific targets.

### Test approach

Each module uses the test methodology most appropriate to its output type (synthetic images, set comparison, structural comparison, exact match). See individual module PRDs for specifics.

---

## Module PRD References

| Module | PRD Location |
|---|---|
| `extract_text_from_image` | `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md` |
| `extract_words_from_text` | `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md` |
| `translate_text` | `nl_processing/translate_text/docs/prd_translate_text.md` |
| `translate_word` | `nl_processing/translate_word/docs/prd_translate_word.md` |
