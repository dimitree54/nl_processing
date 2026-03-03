---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain-skipped', 'step-06-innovation-skipped', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments: ['product-brief-extract_words_from_text-2026-03-01.md']
parentPrd: docs/planning-artifacts/prd.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - extract_words_from_text

**Author:** Dima
**Date:** 2026-03-01

> For shared requirements (structured output, configuration, language support, error handling, NFRs), see the [shared PRD](../../../docs/planning-artifacts/prd.md). This document covers only module-specific requirements.

## Executive Summary

`extract_words_from_text` extracts and normalizes words from Markdown-formatted text. Given Markdown text in a known language, it returns a flat list of `WordEntry` objects (from `core`) containing a normalized form and a word type. Markdown formatting is transparently ignored — the LLM extracts only linguistic content. Language-specific normalization rules are defined by prompt JSONs written in the target language. Initial release supports Dutch only.

### What Makes This Special

No existing solution combines LLM-powered normalization, a flat word-type taxonomy, prompt-driven language extensibility, and a zero-config interface in a single module. Traditional NLP tools require per-language setup and lack language-specific normalization conventions (e.g., Dutch de/het articles for nouns). Here, adding a language is a linguistic task, not an engineering one.

## Success Criteria

### Technical Success

- 100% extraction accuracy on 5 short test cases (1–2 sentences each), validated as set comparison (normalized form + word type)
- Each test case covers diverse word types (nouns with de/het, verbs, adjectives, prepositions, proper nouns, compound expressions)
- <5 seconds processing time for ~100-word text (separate performance test)
- Non-target language text returns an empty list

### Measurable Outcomes

| Metric | Target | Measurement |
|---|---|---|
| Extraction accuracy | 100% exact match (normalized) | 5 synthetic test cases, set comparison |
| Extraction latency | < 5 seconds per ~100 words | Benchmark timing |
| Integration time | Minutes | Docstring completeness |

## Scope

All features are required — no phased MVP. The module either works completely or is not ready.

**Risk Mitigation:**
- **Technical:** LLM output variability — mitigated by set-based comparison testing (no order/deduplication enforcement)
- **Resource:** Single-developer module with limited scope — low risk

**Growth (Post-Release):**
- Additional language support via new prompt JSONs (each language with its own normalization logic and per-word metadata)

## User Journeys

### Journey 1: First Integration (Happy Path)

**Alex, backend developer**, is building a document processing pipeline. He needs to extract and normalize Dutch words from text.

**Opening Scene:** Alex finds `extract_words_from_text` in the nl_processing project. Reads the docstring — import the class, instantiate with defaults, call one method. Three lines of code.

**Rising Action:** Alex writes a quick test — passes Dutch Markdown text. Gets a flat list of `WordEntry` objects: each word normalized (nouns with de/het, verbs as infinitives), type assigned (noun, verb, proper_noun_person, preposition...). Markdown formatting ignored.

**Climax:** Alex drops the module into his pipeline, replacing manual parsing logic. Works on the first try. Filters by type — removes prepositions, keeps only nouns and verbs.

**Resolution:** The module becomes an invisible part of the pipeline. Text in, structured words out.

### Journey 2: Error Handling

**Alex** processes texts from various sources. Some contain only English text, sometimes the API is unavailable.

**Opening Scene:** Alex's pipeline starts processing. Most texts return correct word objects.

**Rising Action:** English text — module returns an empty list. API rate limit — `APIError` is raised. Each case is handled in Alex's code through standard checks.

**Climax:** Empty lists and typed exceptions cover all failure modes. The pipeline handles errors gracefully.

**Resolution:** The pipeline runs reliably. Successful calls yield word objects, errors are logged with clear messages, the pipeline never crashes unexpectedly.

### Journey Requirements Summary

| Capability | Revealed By |
|---|---|
| Zero-config instantiation | Journey 1 |
| Single extraction method (text in, `WordEntry` objects out) | Journey 1 |
| Flat word-type taxonomy with filtering | Journey 1 |
| Markdown-transparent extraction | Journey 1 |
| Language-specific normalization (de/het, infinitives) | Journey 1 |
| Empty list for non-target language | Journey 2 |
| `APIError` (from `core`) | Journey 2 |

## Developer Tool Specific Requirements

### API Surface

**Public interface:**

```python
from nl_processing.extract_words_from_text.service import WordExtractor

extractor = WordExtractor()
words = extractor.extract(text)
```

**Constructor (all parameters optional, sensible defaults):**
- `model` — LLM model name (default: `gpt-5-nano`). GPT-5 Mini is used as an evaluation baseline; the default is downgraded to the cheapest model that still passes quality gates.
- `language` — target language as `Language` enum from `core` (default: `Language.NL`)

**Return type:** flat list of `WordEntry` objects (from `core`), each containing:
- `normalized_form` — normalized word (e.g., "de fiets", "lopen")
- `word_type` — flat type string (e.g., noun, verb, adjective, preposition, proper_noun_person, proper_noun_country, conjunction, etc.)

**Exceptions:** `APIError` from `core` for upstream API failures.

### Implementation Considerations

- No module-specific dependencies beyond `core`
- Language-specific prompts stored as JSON in module directory, loaded by `core` utilities
- Uses LangChain directly for all LLM interaction; `core` provides shared models/exceptions and the prompt loading utility.

## Functional Requirements

### Text Extraction

- FR1: Developer can extract words from a Markdown-formatted text by providing a string input
- FR2: Module extracts only words in the specified target language from the text
- FR3: Module ignores text in languages other than the target language and returns an empty list
- FR4: Module ignores Markdown formatting and extracts only linguistic content
- FR5: Module extracts compound expressions and phrasal constructs as single word units

### Word Normalization

- FR6: Module normalizes each extracted word according to language-specific rules
- FR7: Module normalizes Dutch nouns with their article (de/het)
- FR8: Module normalizes Dutch verbs to infinitive form
- FR9: Each `WordEntry` contains a normalized form and a word type

### Word Type Taxonomy

- FR10: Module assigns a flat word type to each extracted word (noun, verb, adjective, preposition, conjunction, proper_noun_person, proper_noun_country, etc.)
- FR11: Word types are flat strings — no nested structures or hierarchies

### Testing & Benchmarking

- FR12: Module includes 5 short test cases (1–2 sentences each) with 100% set-based accuracy validation (normalized form + word type)
- FR13: Module includes a separate performance test for ~100-word text completing in <5 seconds
- FR14: Each test case covers a variety of word types (nouns with de/het, verbs, adjectives, prepositions, proper nouns, compound expressions)

## Non-Functional Requirements (Module-Specific)

### Performance

- NFR1: Each extraction call completes in <5 seconds wall clock time for ~100-word text
- NFR2: Module does not perform unnecessary text processing that adds latency
