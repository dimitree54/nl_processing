---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish']
inputDocuments: ['product-brief-translate_word-2026-03-01.md']
parentPrd: docs/planning-artifacts/prd.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: low
  projectContext: greenfield
---

# Product Requirements Document - translate_word

**Author:** Dima
**Date:** 2026-03-01

> For shared requirements (structured output, configuration, language support, error handling, NFRs), see the [shared PRD](../../../docs/planning-artifacts/prd.md). This document covers only module-specific requirements.

## Executive Summary

`translate_word` translates normalized words and short phrases between languages. It accepts a list of `Word` objects (from `core`) and returns a list of `Word` objects — one-to-one, preserving input order. The module uses language-specific few-shot prompt JSONs for high-quality translations. Each output `Word` contains the Russian `normalized_form`, a `PartOfSpeech` word type determined by the LLM, and `language=Language.RU`. Initial release supports Dutch→Russian only. Performance target: <1 second for 10 words.

### What Makes This Special

- **LLM translation quality for individual words:** Captures nuance and context-appropriate meanings that algorithmic services miss at the word level
- **Unified pipeline model:** Uses the same `Word` model as `extract_words_from_text`, creating a seamless pipeline from extraction to translation
- **One-to-one batch processing:** Structured output via Pydantic tool calling guarantees clean input→output mapping — no missing or extra items

## Success Criteria

### Technical Success

- **Translation accuracy:** 100% exact match on 1 test case containing 10 unambiguous Dutch words/phrases translated to Russian
- **Performance:** Translation of 10 words completes in <1 second (wall clock time)
- **Output structure:** Each input `Word` maps to exactly one output `Word` in the output list, preserving order
- **Error behavior:** Empty input returns empty list; upstream API failures raise `APIError`

### Measurable Outcomes

- Quality test case (10 words): 100% exact match — binary pass/fail
- Performance test (10 words): <1 second — binary pass/fail
- Module is usable with zero configuration beyond source/target language enums

## Scope

**MVP Approach:** Single, indivisible module. No phased delivery.

**Resource Requirements:** Single developer.

### Risk Mitigation

- **Technical:** LLM translation quality variability — mitigated by exact-match test case with unambiguous words and few-shot prompting
- **Resource:** Minimal — single developer, no complex infrastructure

### Growth Features (Post-Release)

- Additional fields in `Word` (usage examples, synonyms, alternative translations)
- Additional language pairs via new prompt JSONs with few-shot examples

## User Journeys

### Journey 1: The Integration Developer — Success Path

**Alex**, a Python developer on the `nl_processing` project, is building a pipeline that processes Dutch text — extracting words and then translating them to Russian. No LLM background.

**Opening Scene:** Alex has a working pipeline using `extract_words_from_text`. Now needs to translate those words. Finds `translate_word` in project docs.

**Rising Action:** Opens README, sees quick-start example:
```python
from nl_processing.translate_word.service import WordTranslator
from nl_processing.core.models import Language

translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)
words = [Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL), ...]
results = translator.translate(words)
# results[0].normalized_form → "дом"
# results[0].word_type → PartOfSpeech.NOUN
# results[0].language → Language.RU
```

**Climax:** First call returns a list of `Word` objects — one per input word, in order, each with a correct Russian translation. No extra setup, no debugging.

**Resolution:** Integrated in under 10 minutes. Module becomes an invisible, reliable component.

### Journey 2: The Integration Developer — Error Handling

**Alex** passes an empty list — gets empty list back, no crash. Later, OpenAI API key expires — `APIError` with clear message. Alex catches it, logs it, recovery is straightforward.

### Journey Requirements Summary

| Capability | Revealed By |
|---|---|
| `WordTranslator` class with `Language` enum constructor | Success path |
| Single translate method: `list[Word]` → `list[Word]` | Success path |
| One-to-one order-preserving mapping | Success path |
| Empty input → empty output | Error handling |
| Typed `APIError` (from `core`) | Error handling |

## Developer Tool Specific Requirements

### API Surface

**Public Interface:**

- `WordTranslator` class
  - Constructor: `__init__(source_language: Language, target_language: Language, model: str = "gpt-5-nano")` — `Language` from `core`, optional model override (baseline evaluation starts from GPT-5 Mini, then downgrades to the cheapest model that still passes quality gates)
  - Method: `translate(words: list[Word]) -> list[Word]` — `Word` from `core`

`Language`, `Word`, `PartOfSpeech`, and `APIError` are imported from `core`.

**Behavioral Contract:**
- One-to-one order-preserving mapping: `len(output) == len(input)`, same order
- Empty input → empty output (no exception)
- Upstream API failures → `APIError`

### Implementation Considerations

- Pydantic `Word` model defined in `core` — used as public API input/output type. Internal `_LLMTranslationEntry` model (without `language` field) used for LangChain tool calling
- Language-specific prompt JSONs with few-shot examples stored in module directory, loaded by `core` utilities
- No module-specific dependencies beyond `core`

## Functional Requirements

### Word Translation

- FR1: Developer can instantiate `WordTranslator` with source and target `Language` enums (from `core`)
- FR2: Developer can call a single translate method with a list of `Word` objects and receive a list of `Word` objects
- FR3: System translates each input word with one-to-one order-preserving mapping
- FR4: System returns `Word` objects (from `core`) containing `normalized_form`, `word_type` (`PartOfSpeech`), and `language`

### Language Configuration

- FR5: System supports Dutch (NL) as source and Russian (RU) as target on initial release
- FR6: Developer can optionally override the default LLM model name via constructor parameter

### Prompt Engineering

- FR7: System uses language-specific few-shot prompt JSONs for translation
- FR8: Prompt architecture supports adding new language pairs by adding new prompt JSONs without code changes

### Error Handling (Module-Specific)

- FR9: System returns an empty list when input is an empty list

### Quality & Testing

- FR10: System passes a quality test case of 10 unambiguous Dutch words with 100% exact match against ground truth Russian translations
- FR11: System completes translation of 10 words in less than 1 second

## Non-Functional Requirements (Module-Specific)

### Performance

- NFR1: Translation of a batch of 10 words completes in <1 second wall clock time (including network round-trip)
- NFR2: Single LLM call per translate invocation — all words in one batch, not individual calls per word
