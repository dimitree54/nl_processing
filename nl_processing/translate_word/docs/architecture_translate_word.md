---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-02'
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/translate_word/docs/product-brief-translate_word-2026-03-01.md
  - nl_processing/translate_word/docs/prd_translate_word.md
workflowType: 'architecture'
project_name: 'nl_processing'
user_name: 'Dima'
date: '2026-03-02'
scope: 'translate_word'
parentArchitecture: docs/planning-artifacts/architecture.md
---

# Architecture Decision Document — translate_word

> For shared architectural decisions (core package, code style, patterns, project structure), see the [shared architecture](../../../docs/planning-artifacts/architecture.md). This document covers only module-specific decisions.

---

## Module-Specific Architectural Decisions

### Decision: Single LLM Call Per Batch — All Words in One Request

The `translate()` method sends all input words in a single LLM call, not one call per word.

**Rationale:** (1) Performance — 10 words in <1 second requires batching. Individual calls would exceed the target. (2) Cost — one API call vs N calls. (3) LangChain's `with_structured_output()` can enforce a list schema in a single response.

### Decision: One-to-One Order-Preserving Mapping

The output `list[TranslationResult]` must have exactly `len(output) == len(input)` with the same order. This is enforced by the Pydantic schema and prompt instructions.

**Implication:** The prompt must explicitly instruct the LLM to return exactly one translation per input word, in the same order. The Pydantic output schema enforces the list structure; the prompt enforces ordering and one-to-one correspondence.

### Decision: Source + Target Language Constructor

Same pattern as `translate_text` — `WordTranslator` requires both `source_language` and `target_language`:

```python
translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)
```

### Decision: `TranslationResult` — Minimal Pydantic Model, Extensible

`TranslationResult` (from `core`) currently contains only `translation: str`. It is a Pydantic model (not a plain string) to enable future field additions (usage examples, synonyms, alternative translations) without breaking the public interface.

### Decision: Empty List for Empty Input

Empty input list → empty output list (no error, no API call).

### Decision: Prompt File Naming — Language Pair

Same convention as `translate_text`: `nl_ru.json`.

### Decision: No Module-Specific Dependencies

This module has no dependencies beyond `core` and `langchain`/`langchain-openai`.

---

## Module Internal Structure

```
nl_processing/translate_word/
├── __init__.py              # empty
├── service.py               # WordTranslator (public class)
├── prompts/
│   └── nl_ru.json           # Dutch→Russian word translation prompt with few-shot examples
└── docs/
    ├── product-brief-translate_word-2026-03-01.md
    ├── prd_translate_word.md
    └── architecture_translate_word.md  # THIS DOCUMENT
```

---

## Test Strategy

- **Unit tests:** Mock LangChain chain invocation. Test empty-input handling, one-to-one mapping enforcement, error mapping.
- **Integration tests:** Real API calls. Quality test: 10 unambiguous Dutch words with 100% exact match against ground truth Russian translations. Performance test: 10 words in <1 second.
- **E2e tests:** Full translation scenarios with word lists from upstream pipeline.
