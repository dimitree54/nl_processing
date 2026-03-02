---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: []
date: 2026-03-01
author: Dima
parentBrief: docs/planning-artifacts/product-brief.md
---

# Product Brief: translate_word

> For shared project context (technology stack, target users, design principles), see the [shared product brief](../../../docs/planning-artifacts/product-brief.md).

## Executive Summary

`translate_word` is a module that translates normalized words and short phrases between languages. It accepts a list of normalized source-language words/phrases and returns a list of `TranslationResult` objects (from `core`) — one-to-one, preserving input order. The module uses language-specific few-shot prompt JSONs for high-quality translations. `TranslationResult` currently contains only a `translation` field, with the structure designed for future field extensions without breaking the interface. Initial release supports Dutch→Russian only. Performance target: <1 second for 10 words.

### What Makes This Module Special

- **LLM translation quality for individual words:** Captures nuance and context-appropriate meanings that algorithmic services miss at the word level
- **Extensible result objects:** `TranslationResult` (from `core`) is a structured Pydantic model, not a plain string — ready for future field additions (usage examples, synonyms) without interface changes
- **One-to-one batch processing:** Structured output guarantees clean input→output mapping — no missing or extra items
- **Few-shot prompting:** Language-specific prompts with embedded translation examples ensure consistent output

---

## Core Vision

### Problem Statement

Developers in the `nl_processing` project need a reliable, high-quality way to translate individual normalized words and short phrases. The input comes from upstream modules (e.g., `extract_words_from_text`). While LLMs produce significantly better word-level translations than algorithmic services, calling an LLM directly is unreliable due to unstructured output and lack of batch processing semantics.

### Problem Impact

- Raw LLM calls produce unpredictable output format for multiple words — inconsistent ordering, extra commentary, missing items
- No built-in mechanism to enforce one-to-one mapping between input words and output translations
- Algorithmic translation services lack quality for individual word translation

### Why Existing Solutions Fall Short

- **Algorithmic translation APIs:** Lower quality for individual words — miss nuance, no control over output structure
- **Direct LLM calls without structure:** Unreliable format, no one-to-one mapping guarantee
- **Dictionary APIs:** Limited vocabulary, no handling of normalized forms or short phrases

### Proposed Solution

A Python module that:
- Provides `WordTranslator` class with `Language` enum constructor (from `core`)
- Exposes a single translation method: list of words in → list of `TranslationResult` objects out (one-to-one, order-preserving)
- Uses the `core` prompt execution engine with language-specific few-shot prompt JSONs
- Returns empty list when input is empty
- Raises `APIError` (from `core`) for upstream API failures
- Performance target: <1 second for 10 words

---

## Success Metrics

### Acceptance Criteria

- **Translation accuracy:** 100% exact match on 1 test case containing 10 unambiguous Dutch words translated to Russian
- **Performance:** 10 words in <1 second
- **Output structure:** One-to-one order-preserving mapping: `len(output) == len(input)`
- **Error behavior:** Empty input → empty list; API failures → `APIError`

---

## Scope

This module has no MVP/phased delivery — it is a single, indivisible unit.

### Core Features

1. **Word Translation (Dutch → Russian):** Translate a list of normalized words/phrases, return `TranslationResult` objects preserving order
2. **`WordTranslator` class** with `Language` enum constructor, single translate method
3. **Language-specific few-shot prompt JSONs** for consistent, high-quality translations
4. **Error handling:** Empty input → empty list; API failures → `APIError`
5. **Quality test:** 1 test case (10 words, exact match) + performance test (<1s)

### Out of Scope

- Language pairs other than Dutch→Russian
- Additional fields in `TranslationResult` beyond `translation`
- Deduplication or ordering guarantees beyond preserving input order
- Batch size limits or chunking logic

### Future Vision

- Additional language pairs via new prompt JSON files
- Additional fields in `TranslationResult` (usage examples, synonyms, alternative translations)
- No planned versioning cycle — features added incrementally
