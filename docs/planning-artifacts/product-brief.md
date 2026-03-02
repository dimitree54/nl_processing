---
date: 2026-03-01
author: Dima
---

# Product Brief: nl_processing

## Executive Summary

`nl_processing` is a Python project containing a pipeline of internal modules for language-specific text processing powered by LLM capabilities (OpenAI API via LangChain). The project provides a set of composable, black-box modules — each with a minimal public interface, zero-config defaults, and structured output enforcement via Pydantic. A shared `core` package provides the common infrastructure: LLM prompt execution engine, Pydantic models for all module interfaces, exceptions, and prompt management utilities. All modules share a common technical foundation and design philosophy: a developer with no LLM or NLP knowledge can integrate any module in minutes.

The initial release targets Dutch as the source language and Russian as the translation target, with all modules designed for language extensibility via prompts — adding a new language is a linguistic task, not an engineering one.

### Pipeline Overview

The modules form a sequential processing pipeline:

1. **`extract_text_from_image`** — Extracts text from images using LLM vision capabilities. Image in, markdown-formatted text out.
2. **`extract_words_from_text`** — Extracts and normalizes words from markdown text. Text in, structured word objects out.
3. **`translate_text`** — Translates text between languages with markdown preservation. Text in, translated text out.
4. **`translate_word`** — Translates normalized words and short phrases. Word list in, translation result objects out.

Each module is independently usable — the pipeline is composable, not monolithic.

### Shared Core (`nl_processing/core/`)

All modules delegate LLM interaction, structured output, error handling, and prompt management to a shared `core` package. This means:
- No module directly imports LangChain or OpenAI — all LLM calls go through `core`
- All Pydantic interface models (input/output schemas for every module) are defined in `core`
- All exceptions (`APIError`, `TargetLanguageNotFoundError`, etc.) are defined in `core`
- Prompt files (multi-message few-shot JSONs) are stored per-module, loaded by `core` utilities

---

## Core Vision

### Problem Statement

Developers building language processing pipelines face fragmented tooling: classical OCR lacks contextual understanding, traditional NLP tools (spaCy, NLTK) require per-language toolchain setup, and algorithmic translation services (Google Translate, DeepL) produce lower quality for nuanced content. Calling LLMs directly is unreliable for programmatic use — models add conversational "chatter" and produce unstructured output.

### Proposed Solution

A set of Python modules that:
- Use LLM capabilities (GPT-5 Mini baseline via LangChain) for higher quality than traditional tools
- Enforce structured output via Pydantic tool calling — no conversational prefixes/suffixes
- Expose minimal public interfaces with sensible defaults — zero-config primary usage
- Use language-specific prompts written in the target language — extensible by adding prompts, not code
- Provide typed exceptions for all error conditions
- Share a common `core` package for LLM infrastructure, models, and exceptions — no duplication across modules

### Key Differentiators

- **LLM-powered quality** — contextual understanding, language-aware processing, natural output
- **Structured output discipline** — Pydantic/LangChain `with_structured_output()` guarantees clean programmatic results
- **Prompt-driven language extensibility** — new language = new prompt, not new toolchain
- **Zero-config developer experience** — import, instantiate with defaults, call one method, get results
- **Composable pipeline** — each module works independently or as part of a chain
- **Shared infrastructure** — `core` package eliminates duplication; modules focus on domain logic only

---

## Target Users

### Primary Users

**The Integration Developer**

A Python developer building text processing pipelines who needs language processing as a component. No LLM, NLP, or AI expertise required.

**Profile:**
- Role: Python developer integrating modules into a larger application or pipeline
- Skill level: Any level; no NLP or LLM expertise required
- Goal: Add language processing capabilities with minimal learning curve
- Environment: Working within the `nl_processing` project codebase

**Success Vision:**
- Import a class, instantiate with defaults, call one method, get results
- Total time from discovery to working integration: minutes
- A brief README with a quick-start example is sufficient

### Secondary Users

N/A — all modules are designed exclusively for integration developers as consumers. Internal development (prompt tuning, benchmarking, model selection) is a development concern, not a user concern.

---

## Technical Foundation

### Technology Stack

- **Python 3.12+**
- **LangChain + langchain-openai** — LLM orchestration layer. All API communication goes through LangChain, enabling model swap without code changes
- **OpenAI API** (GPT-5 Mini baseline) — LLM provider
- **Pydantic** — structured output enforcement via LangChain tool calling, and all public interface models
- **Authentication:** `OPENAI_API_KEY` environment variable, managed via Doppler CLI
- **Secrets Management:** Doppler CLI for all environment variables — no `.env` files

### Architecture: Core Package (`nl_processing/core/`)

The `core` package provides shared infrastructure. Each module uses LangChain directly for chain construction — `core` does not wrap or mediate LLM access.

**Core provides:**

1. **Public Interface Pydantic Models** — Only models that form module input/output contracts are defined in `core`. Internal models (e.g., intermediate chain schemas) stay in their respective modules. Includes: `ExtractedText`, `WordEntry`, `TranslationResult`, `Language` enum.

2. **All Exceptions** — `APIError` (shared by all modules), `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`, and any future exceptions.

3. **Prompt Loading Utility** — Helper to load prompt JSON files (in LangChain `ChatPromptTemplate` serialization format) from module directories. Each module stores its own prompt files; `core` provides the loading mechanism.

4. **Prompt Authoring Helper** — A dev-time-only script (in `core/scripts/`): the developer writes a temporary Python file with an inline multi-message prompt, runs the helper, and it saves the prompt as a JSON file in the correct format.

### Shared Design Principles

1. **Zero-config primary usage** — all modules work with default parameters out of the box
2. **Minimal public interface** — one class, one or two methods, sensible defaults
3. **Structured output** — Pydantic models eliminate LLM conversational chatter
4. **Language-specific prompts** — prompts written in the target language, stored as JSON per module
5. **Typed exceptions** — all error conditions surface as typed, catchable exceptions from `core`
6. **Black-box design** — consumers need no knowledge of LLM, LangChain, or module internals
7. **LangChain direct usage** — each module builds its own LangChain chains; model swappable via constructor parameter

### Shared Conventions

- Internal modules within `nl_processing` — no PyPI publishing, no standalone packaging
- Dependencies managed at project level
- Each module includes quality test suites as release prerequisites
- Short README/docstrings — no documentation of internals or extension mechanisms
- Language extensibility via new prompt JSON files (linguistic task, not engineering task)
- Prompts stored as multi-message few-shot JSON files in each module's directory, loaded by `core`

### Project Classification

- **Project Type:** Developer tool (internal Python modules)
- **Domain:** Scientific (ML-AI powered linguistic processing)
- **Project Context:** Greenfield
- **Business Objectives:** N/A — internal utility modules. Success is binary: tests pass, modules work with default configuration

---

## Module Summary

| Module | Input | Output | Initial Language | Key Feature |
|---|---|---|---|---|
| `core` | (infrastructure) | (infrastructure) | N/A | LLM engine, models, exceptions, prompt utils |
| `extract_text_from_image` | Image (path or cv2 array) | Markdown text | Dutch | LLM vision extraction |
| `extract_words_from_text` | Markdown text | Word objects (normalized form + type) | Dutch | Flat word-type taxonomy |
| `translate_text` | Text | Translated text | Dutch → Russian | Markdown-preserving translation |
| `translate_word` | Word list | Translation result objects | Dutch → Russian | One-to-one batch translation |

For module-specific details (API surface, error handling, success criteria, functional requirements), see each module's dedicated product brief and PRD.

---

## Success Metrics

### Shared Acceptance Pattern

All modules follow the same quality gate pattern:
- Module-specific test suite must pass with 100% accuracy as a prerequisite for any release
- Performance targets defined per module based on processing characteristics
- API errors from OpenAI surfaced as clear, typed `APIError` exceptions from `core`

### Readiness Criteria (All Modules)

- All quality tests pass
- README/docstrings with quick-start example exist
- API errors produce clear, typed exception messages
- Module is usable with zero configuration beyond defaults

---

## Future Vision

- Additional language support across all modules (new prompt JSON files and test suites per language)
- Pipeline-level integration and orchestration
- Architecture designed for language extensibility with minimal effort per new language
- Rich result objects with additional fields (usage examples, synonyms) — structure already designed for extensibility
