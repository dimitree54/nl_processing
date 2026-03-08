---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain-skipped, step-06-innovation-skipped, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish, step-12-complete]
inputDocuments: [product-brief-translate_text-2026-03-01.md]
parentPrd: docs/planning-artifacts/prd.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - translate_text

**Author:** Dima
**Date:** 2026-03-01

> For shared requirements (structured output, configuration, language support, error handling, NFRs), see the [shared PRD](../../../docs/planning-artifacts/prd.md). This document covers only module-specific requirements.

## Executive Summary

`translate_text` provides high-quality LLM-powered text translation with markdown formatting preservation. The developer instantiates `TextTranslator` with source and target `Language` enums (from `core`), then calls one method — text in, translated text out. The translation prompt uses few-shot examples to produce natural, human-sounding output that stays close to the original meaning and structure. Initial release supports Dutch-to-Russian translation only.

### What Makes This Special

- **Controllable, "alive" translation:** LLM-based translation produces more natural, context-aware results than algorithmic services, and the style is fully controllable through few-shot examples
- **Prompt-as-product:** The prompt (including few-shot examples) is the core intellectual property. Few-shot examples simultaneously serve as training data for the model and as test cases for quality validation
- **Language pair extensibility by design:** Adding a new language pair means adding a new prompt JSON file with few-shot examples and corresponding tests — no code changes

## Success Criteria

### Technical Success

- **Output cleanliness:** Every translation call returns only the translated text — no conversational prefixes/suffixes
- **Script correctness:** For a curated Dutch test input (no proper nouns), the Russian output contains only Cyrillic characters, punctuation, whitespace, and markdown symbols
- **Markdown preservation:** Translated output preserves the same markdown structure as input (headings, bold, italic, lists, paragraph breaks)
- **Performance:** ~100 words completes in < 5 seconds
- **Error handling:** Empty input or non-Dutch text returns empty string; upstream API failures raise `APIError`
- **Translation style:** Natural, human-sounding Russian, close to original meaning — no creative rewriting. Validated by human review of the few-shot example set

### Measurable Outcomes

| Criterion | Target | Validation Method |
|---|---|---|
| No LLM chatter in output | 100% of calls | Structured output enforcement via Pydantic tool calling (LangChain tools) |
| Cyrillic-only output (test case) | Pass | Regex check on curated test without proper nouns |
| Markdown structure preserved | Pass | Structural comparison on curated markdown test |
| Translation latency (~100 words) | < 5 seconds | Wall clock timing in test |
| Unsupported language pair | Exception raised | Unit test with non-nl/ru pair |
| Empty/non-Dutch input | Empty string returned | Unit test |
| API failure | `APIError` raised | Mock test |

## Scope

### MVP Feature Set

**Core User Journeys Supported:**
- Journey 1 (Success Path): Full integration flow — import, instantiate, translate, get clean result
- Journey 2 (Edge Case): Empty input, non-Dutch input, API failure handling

**Resource Requirements:** Single developer, 1 sprint.

### Growth Features (Post-Release)

- Additional language pairs (new prompt JSONs + few-shot examples + tests per pair)
- Markdown-aware translation policy (preserve code blocks untranslated)
- Terminology/glossary support for domain-specific translation

### Risk Mitigation

- *Prompt quality:* Start with a small set of curated few-shot examples, validate with human review, iterate before finalizing
- *Structured output reliability:* Pin model version in defaults, test structured output compliance in acceptance tests

## User Journeys

### Journey 1: Integration Developer — Success Path

**Alexei, Python developer** building a text processing pipeline. He needs to translate Dutch article summaries into Russian for a downstream analytics module. No LLM experience.

**Opening Scene:** Alexei finds `translate_text` referenced in project docs.

**Rising Action:** He opens the README, sees a 5-line quick-start example:
```python
from nl_processing.translate_text.service import TextTranslator
from nl_processing.core.models import Language

translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
result = translator.translate(dutch_text)
```
No configuration files, no API keys to manage (already set at project level).

**Climax:** The translated Russian text comes back clean — no "Here is the translation:" prefix, markdown headings preserved, natural-sounding Russian.

**Resolution:** Alexei integrates the module in under 10 minutes. He never looks at the module internals again.

### Journey 2: Integration Developer — Edge Case / Error Recovery

**Alexei**, two weeks later. Pipeline processes a batch with mixed-language content.

**Rising Action:** For empty body, `translate("")` returns empty string. For English text, returns empty string. Pipeline continues without crashing. Alexei notices missing translations in output.

**Climax:** He adds a language-check step upstream. The module's empty-string behavior made the issue visible without crashing.

**Resolution:** OpenAI API rate-limit spike → `APIError` with clear message. Alexei adds retry logic.

### Journey Requirements Summary

| Journey | Capabilities Revealed |
|---|---|
| Success Path | Simple class instantiation, single translate method, clean output, markdown preservation, zero-config DX |
| Edge Case | Graceful empty input handling, non-target-language handling (empty string), typed `APIError`, clear error messages |

## Developer Tool Specific Requirements

### API Surface

The module exposes exactly three public symbols:

| Symbol | Type | Description |
|---|---|---|
| `TextTranslator` | class | Constructor requires `source_language: Language`, `target_language: Language` (from `core`). Optional model param with default. |
| `translate(text: str) -> str` | method | Translates input text. Returns translated string or empty string. |

`Language` enum and `APIError` exception are imported from `core`.

Everything else is internal (`_`-prefixed and not re-exported from the package `__init__.py`). Public imports should target `service.py` directly.

### Implementation Considerations

- **Prompt file:** Translation prompt with few-shot examples stored as JSON in module directory, loaded by `core` utilities
- **Model configuration:** Default model is `gpt-5-nano` (baseline evaluation starts from GPT-5 Mini, then downgrades to the cheapest model that still passes quality gates). Optional constructor param allows override.
- No module-specific dependencies beyond `core`

## Functional Requirements

### Translation Core

- FR1: Developer can translate Dutch text to Russian by calling a single method with text input
- FR2: Translated text preserves the markdown formatting of the input (headings, bold, italic, lists, paragraph breaks)
- FR3: Translated text reads as natural Russian while staying close to the original meaning and structure
- FR4: Translated text contains only the translation — no conversational prefixes, suffixes, or explanations

### Module Interface

- FR5: Developer instantiates the translator by providing source and target language as `Language` enum values (from `core`)
- FR6: Module rejects unsupported language pair combinations with a descriptive exception at instantiation time

### Input Handling

- FR7: Empty string input returns empty string (no error)
- FR8: Text with no Dutch content returns empty string (no error)

### Translation Style

- FR9: Translation prompt uses few-shot examples stored as JSON to produce natural, human-sounding Russian
- FR10: Translation stays close to original meaning and structure — no creative rewriting, no added content

## Non-Functional Requirements (Module-Specific)

### Performance

- NFR1: Translation of ~100-word text completes in < 5 seconds wall clock time
- NFR2: Module instantiation (`TextTranslator` constructor) completes in < 1 second (no API calls at init time)
