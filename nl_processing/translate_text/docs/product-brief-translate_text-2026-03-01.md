---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
date: 2026-03-01
author: Dima
parentBrief: docs/planning-artifacts/product-brief.md
---

# Product Brief: translate_text

> For shared project context (technology stack, target users, design principles), see the [shared product brief](../../../docs/planning-artifacts/product-brief.md).

## Executive Summary

`translate_text` is a module that provides high-quality LLM-powered text translation with markdown formatting preservation. The developer instantiates `TextTranslator` with source and target `Language` enums (from `core`), then calls one method — text in, translated text out. The translation prompt uses few-shot examples to produce natural, human-sounding output that stays close to the original meaning and structure. Initial release supports Dutch-to-Russian translation only; new language pairs are added by creating new prompt JSON files and test cases.

### What Makes This Module Special

- **Controllable, "alive" translation:** LLM-based translation produces more natural, context-aware results than algorithmic services, and the translation style is fully controllable through prompt engineering and few-shot examples
- **Prompt-as-product:** The prompt (including few-shot translation examples) is the core intellectual property of this module. Few-shot examples simultaneously serve as training data for the model and as test cases for translation quality validation
- **Markdown formatting preservation:** Translation preserves headings, bold, italic, lists, paragraph breaks from source to output

---

## Core Vision

### Problem Statement

Developers in the `nl_processing` project need a convenient, high-quality text translation component that preserves markdown formatting. While LLMs produce significantly better translations than algorithmic services, calling an LLM directly is unreliable for programmatic use — models tend to add conversational prefixes/suffixes, and there is no enforcement of output structure or formatting preservation.

### Problem Impact

- Raw LLM translation calls produce unpredictable output with conversational "chatter"
- No built-in mechanism to enforce that the output contains only the translated text
- Markdown formatting is easily lost during translation without explicit prompting
- Each developer who needs translation must independently solve the same prompt engineering problems

### Why Existing Solutions Fall Short

- **Algorithmic translation APIs (Google Translate, DeepL):** Lower translation quality — especially for nuanced text, context-dependent phrasing, and tone/style preservation. No native markdown formatting preservation
- **Direct LLM calls without structure:** Conversational prefixes/suffixes make raw output unreliable

### Proposed Solution

A Python module that:
- Provides `TextTranslator` class with `Language` enum constructor (from `core`)
- Exposes a single translation method: text in, translated text out
- Uses the `core` prompt execution engine with language-specific few-shot prompt JSONs
- Preserves markdown formatting from source to translated text
- Returns empty string when input is empty or contains no text in the source language
- Raises `APIError` (from `core`) for upstream API failures

---

## Success Metrics

### Acceptance Criteria

- **Output cleanliness:** Output contains only the translated text — no conversational prefixes/suffixes
- **Script correctness (Dutch → Russian):** For a curated Dutch test input with no proper nouns, the output contains only Cyrillic characters plus allowed punctuation, whitespace, and markdown symbols
- **Markdown preservation:** Translated output preserves the same markdown structure as input
- **Performance:** ~100 words completes in < 5 seconds
- **Error behavior:** Empty input or no Dutch text returns empty string; upstream API failures raise `APIError`
- **Translation style:** Natural, human-sounding Russian that stays close to the original — no creative rewriting

---

## Scope

### Core Features

- **`TextTranslator` class** with `Language` enum constructor, single `translate(text: str) -> str` method
- **Dutch → Russian translation** with carefully engineered few-shot prompt JSON
- **Markdown formatting preservation** from source to translated text
- **Translation style:** Natural, human-sounding Russian, close to original meaning and structure. No creative rewriting, no added content. Controlled via few-shot examples in prompt
- **Error handling:** Empty/non-Dutch input → empty string; API failures → `APIError`
- **Curated test cases:** Cyrillic-only check, markdown preservation, performance

### Out of Scope

- Language pairs other than Dutch → Russian
- Terminology/glossary support and domain-specific translation rules
- Special handling for markdown code blocks
- Automated semantic translation quality scoring
- Batch translation, chunking/streaming, caching

### Future Vision

- Additional language pairs by adding prompt JSON files + tests
- Optional markdown-aware translation policy (preserve code blocks untranslated)
- Optional terminology/glossary support
- Richer evaluation harness (human-reviewed golden sets, regression tracking)
