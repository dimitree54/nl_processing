---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-02'
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/extract_words_from_text/docs/product-brief-extract_words_from_text-2026-03-01.md
  - nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md
workflowType: 'architecture'
project_name: 'nl_processing'
user_name: 'Dima'
date: '2026-03-02'
scope: 'extract_words_from_text'
parentArchitecture: docs/planning-artifacts/architecture.md
---

# Architecture Decision Document — extract_words_from_text

> For shared architectural decisions (core package, code style, patterns, project structure), see the [shared architecture](../../../docs/planning-artifacts/architecture.md). This document covers only module-specific decisions.

---

## Module-Specific Architectural Decisions

### Decision: Flat Word-Type Taxonomy

Word types are flat strings (`"noun"`, `"verb"`, `"adjective"`, `"preposition"`, `"conjunction"`, `"proper_noun_person"`, `"proper_noun_country"`, etc.) — not enums, not hierarchical structures.

**Rationale:** Flat strings allow the LLM to assign types naturally via the prompt, and callers can filter by simple string comparison. The taxonomy is extensible via prompts — adding a new type (e.g., `"proper_noun_city"`) requires only a prompt update, no code change.

### Decision: Language-Specific Normalization via Prompt

Normalization rules (Dutch nouns with de/het article, verbs in infinitive form) are entirely defined in the prompt, not in code. The module has no hardcoded normalization logic.

**Implication:** The prompt is the sole authority for what "normalized form" means for a given language. Different languages may have completely different normalization conventions — all handled by the prompt JSON file.

### Decision: Compound Expressions as Single Units

The prompt instructs the LLM to extract compound expressions and phrasal constructs (e.g., phrasal verbs, idiomatic phrases) as single `WordEntry` items, not individual words.

**Implication:** The output list may contain multi-word entries. The `normalized_form` field in `WordEntry` can be a phrase, not just a single word.

### Decision: Empty List for Non-Target Language

When input text contains no words in the target language, the module returns an empty `list[WordEntry]` — no exception. This differs from `extract_text_from_image` which raises `TargetLanguageNotFoundError`.

**Rationale:** For text processing, an empty result is a valid outcome (the text simply had no extractable words in the target language). For image processing, the absence of target-language text is more likely an error condition.

### Decision: Set-Based Test Validation

Quality tests use set comparison (normalized form + word type) — no ordering or deduplication enforcement. This accommodates LLM output variability in ordering while still validating extraction completeness and accuracy.

### Decision: No Module-Specific Dependencies

This module has no dependencies beyond `core` and `langchain`/`langchain-openai`. Text input is plain Python `str`.

---

## Module Internal Structure

```
nl_processing/extract_words_from_text/
├── __init__.py              # empty
├── service.py               # WordExtractor (public class)
├── prompts/
│   └── nl.json              # Dutch word extraction + normalization prompt
└── docs/
    ├── product-brief-extract_words_from_text-2026-03-01.md
    ├── prd_extract_words_from_text.md
    └── architecture_extract_words_from_text.md  # THIS DOCUMENT
```

---

## Test Strategy

- **Unit tests:** Mock LangChain chain invocation. Test that module correctly passes text to chain and returns `list[WordEntry]`. Test empty-list behavior for non-target language.
- **Integration tests:** Real API calls with 5 curated short test cases (1-2 sentences each). Set-based accuracy validation (normalized form + word type). Performance test: ~100 words in <5 seconds.
- **E2e tests:** Full extraction from markdown text, validating diverse word types across test cases.
