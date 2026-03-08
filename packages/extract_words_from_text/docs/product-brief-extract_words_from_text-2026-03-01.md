---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: []
date: 2026-03-01
author: Dima
parentBrief: docs/planning-artifacts/product-brief.md
---

# Product Brief: extract_words_from_text

> For shared project context (technology stack, target users, design principles), see the [shared product brief](../../../docs/planning-artifacts/product-brief.md).

## Executive Summary

`extract_words_from_text` is a module that extracts and normalizes words from Markdown-formatted text. Given Markdown text in a known language, it returns a flat list of `WordEntry` objects (defined in `core`) containing a normalized form and a word type. Markdown formatting is transparently ignored — the LLM extracts only linguistic content. Language-specific normalization rules are defined by prompts written in the target language — adding a new language requires writing a prompt, not integrating a new NLP toolchain. Initial release supports Dutch only.

### What Makes This Module Special

- **Prompt-driven language extensibility:** New languages are added by writing normalization prompts, not by integrating new NLP toolchains — turning an engineering task into a linguistic one
- **Flat, filterable word-type taxonomy:** Consumers can easily filter by type (exclude prepositions, keep country names but drop person names) without navigating nested structures
- **LLM-powered contextual understanding:** The language model understands compound expressions, phrasal verbs, and idiomatic phrases, extracting them as single units rather than individual words
- **Quality-gated by design:** Built-in set-based test suites per language ensure extraction quality is validated before release

---

## Core Vision

### Problem Statement

There is no readily available, unified solution for extracting and normalizing words from text across multiple languages with consistent output structure. Traditional NLP tools (spaCy, NLTK) require per-language toolchain setup, model selection, and pipeline configuration — and often lack language-specific normalization nuances (e.g., Dutch de/het articles for nouns, proper verb infinitive forms).

### Problem Impact

- Adding support for a new language requires finding, evaluating, and integrating language-specific NLP libraries
- Traditional tools do not capture language-specific normalization conventions without custom post-processing
- No single tool provides a flat, filterable output with word types granular enough to distinguish between e.g., proper nouns (person names vs. country names)

### Why Existing Solutions Fall Short

- **spaCy / NLTK:** Lemmatization and POS tagging exist but require per-language model installation, do not handle language-specific normalization conventions (like de/het)
- **Cloud NLP APIs:** Lack flexibility in defining what "normalization" means for a specific language
- **No existing solution** provides the combination of: LLM-powered normalization, flat word-type taxonomy, and language extensibility via prompts

### Proposed Solution

A Python module that:
- Accepts Markdown-formatted text input with a known source language
- Uses the `core` prompt execution engine with language-specific prompts to extract and normalize words
- Returns a flat list of `WordEntry` objects (from `core`), each with: normalized form and word type
- Provides a minimal public interface: constructor with sensible defaults, single extraction method
- Targets <5 seconds processing time for ~100-word texts
- Includes ~5 set-based quality test cases per language

---

## Success Metrics

### Quality Metrics

- **100% extraction accuracy** on 5 short test cases (1–2 sentences each), validated as set comparison (no order, no deduplication enforcement)
- Each test case contains a variety of word types and validates both normalized form and word type

### Performance Metrics

- **<5 seconds processing time** for a ~100-word text

### Readiness Criteria

- All 5 quality test cases pass with 100% accuracy
- Long-text performance test passes under 5 seconds

---

## Scope

This module has no MVP/phased delivery — it is a single, indivisible unit.

### Core Features

1. **Word Extraction & Normalization (Dutch):** Accept Markdown-formatted Dutch text, extract all words (including compound expressions, phrasal constructs) with language-specific normalization. Markdown formatting transparently ignored
2. **Flat Word-Type Taxonomy:** Each extracted word includes a normalized form and a flat type (noun, verb, adjective, preposition, conjunction, proper_noun_person, proper_noun_country, etc.)
3. **Language-Specific Normalization Rules:** Dutch nouns include de/het article, verbs in infinitive form, encoded in language-specific prompt JSONs
4. **Minimal Public Interface:** Constructor with sensible defaults, single extraction method: text in, list of `WordEntry` objects out
5. **Error Handling:** Text in a non-target language returns an empty list
6. **Quality Test Suite:** 5 short test cases with 100% set-based accuracy validation
7. **Performance Test:** ~100 words completing in <5 seconds

### Out of Scope

- Support for languages other than Dutch
- Deduplication or ordering guarantees in output
- Documentation of internals, prompt engineering, or extension mechanisms

### Future Vision

- Additional language support via new language-specific prompt JSONs
- Architecture designed with inheritance/extensibility for minimal effort per new language
