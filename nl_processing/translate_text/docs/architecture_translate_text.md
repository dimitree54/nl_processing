---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-02'
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/translate_text/docs/product-brief-translate_text-2026-03-01.md
  - nl_processing/translate_text/docs/prd_translate_text.md
workflowType: 'architecture'
project_name: 'nl_processing'
user_name: 'Dima'
date: '2026-03-02'
scope: 'translate_text'
parentArchitecture: docs/planning-artifacts/architecture.md
---

# Architecture Decision Document — translate_text

> For shared architectural decisions (core package, code style, patterns, project structure), see the [shared architecture](../../../docs/planning-artifacts/architecture.md). This document covers only module-specific decisions.

---

## Module-Specific Architectural Decisions

### Decision: Prompt-as-Product — Few-Shot Examples Are the Core Asset

The translation prompt with its few-shot examples is the primary intellectual property of this module. Few-shot examples simultaneously serve as:
1. **Training signal** for the LLM to learn the desired translation style
2. **Test cases** for quality validation — the same examples used in the prompt can be tested for consistency

**Implication:** Prompt engineering and few-shot example curation are the most critical development activities for this module. The code is thin; the prompt carries the value.

### Decision: Markdown Preservation via Prompt Engineering

Markdown formatting preservation (headings, bold, italic, lists, paragraph breaks) is enforced via prompt instructions and few-shot examples — not via pre/post-processing code.

**Rationale:** The LLM can naturally handle markdown preservation when instructed via examples. Code-based markdown parsing and reconstruction would be fragile and add complexity without improving quality.

### Decision: Source + Target Language Constructor

Unlike single-language modules, `TextTranslator` requires both `source_language` and `target_language` in its constructor. This is mandatory (not optional with defaults) because translation is inherently directional.

```python
translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
```

### Decision: Returns Plain `str`, Not Pydantic Model

The `translate()` method returns `str` (the translated text), not a Pydantic wrapper model.

**Rationale:** The output is a single string — wrapping it in a Pydantic model adds no value. Structured output (`with_structured_output()`) is still used internally to enforce clean LLM output (no conversational chatter), but the public interface returns the unwrapped string.

### Decision: Empty String for Edge Cases

- Empty input → empty string (no error)
- Text with no source-language content → empty string (no error)

**Rationale:** These are valid non-error conditions for a translation module. An empty translation is a meaningful result (there was nothing to translate), not a failure.

### Decision: Language Pair Validation at Init Time

Unsupported language pair combinations raise a descriptive exception at `__init__` time — not at `translate()` call time. Fail fast.

### Decision: Prompt File Naming — Language Pair

Prompt files use `<source>_<target>.json` naming: `nl_ru.json`. Each language pair is a separate prompt file with its own few-shot examples.

### Decision: No Module-Specific Dependencies

This module has no dependencies beyond `core` and `langchain`/`langchain-openai`.

---

## Module Internal Structure

```
nl_processing/translate_text/
├── __init__.py              # empty
├── service.py               # TextTranslator (public class)
├── prompts/
│   └── nl_ru.json           # Dutch→Russian translation prompt with few-shot examples
└── docs/
    ├── product-brief-translate_text-2026-03-01.md
    ├── prd_translate_text.md
    └── architecture_translate_text.md  # THIS DOCUMENT
```

---

## Test Strategy

- **Unit tests:** Mock LangChain chain invocation. Test empty-input handling, language pair validation at init, error mapping.
- **Integration tests:** Real API calls. Validate: (1) output cleanliness — no LLM chatter, (2) Cyrillic-only output for test case without proper nouns (regex), (3) markdown structure preservation (structural comparison), (4) performance: ~100 words in <5 seconds.
- **E2e tests:** Full translation scenarios with varied markdown content.

Translation style quality is validated by human review of few-shot examples during prompt development, not by automated tests.
