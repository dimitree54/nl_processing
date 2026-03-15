---
title: "extract_interesting_facts Module Spec"
module_name: "extract_interesting_facts"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
---

# Module Spec: extract_interesting_facts

> This spec describes the module's desired target-state behavior and public contract.
> It defines WHAT the module must do, not HOW it is implemented.
> Document all public interfaces that other modules or end users are expected to use.
> Do not document implementation details such as files, internal classes, helper functions, algorithms, tests, or QA procedures unless the user explicitly requires them.
> Internal-only surfaces do not need full spec coverage, but when they could be mistaken for public API they should be marked as internal or non-contract.

## 1. Module Snapshot

### Summary

`extract_interesting_facts` generates target-language linguistic explanations for caller-provided text whose source language is already known. For single words and short fixed expressions, it returns a detailed lexical analysis with morphology, composition, and usage-oriented facts. For sentence input, it returns a lighter word-by-word gloss plus sentence-level grammar, syntax, idiom, and usage notes instead of a full lexical dossier for every token. Longer text may still be processed on a best-effort basis, but V1 guarantees are centered on lexical items and single sentences.

### System Context

The module sits alongside the existing text-processing packages as an explanation layer for already-known source text. Callers provide the source language, target explanation language, and raw text, then receive one explanation string that is ready for display or further storage. The module does not detect languages, persist results, or own the shared language and exception types used across the repository.

### In Scope

- Public async extractor interface for interesting-facts generation.
- Caller-declared source language and target explanation language.
- Detailed lexical analysis for single-word and short-expression input.
- Lighter token-gloss plus grammar/idiom analysis for sentence input.
- Explicit fail-fast handling for unsupported language pairs, invalid input, and unusable model output.

### Out of Scope

- Automatic language detection or automatic choice of explanation language.
- Persistence, caching, scoring, or spaced-repetition behavior.
- OCR, image input, or audio input.
- Guaranteed analysis shape for multi-sentence or paragraph-length input.
- A machine-readable structured output contract in V1.

### Assumptions

N/A. No unresolved working assumptions remain for this revision.

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `nl_processing.extract_interesting_facts.service.InterestingFactsExtractor(source_language, target_language, model, service_tier)` as its supported public class interface. | Must | Constructor options are part of the caller-facing contract and must match the first-version default configuration style used by `translate_text`. |
| FR-2 | The module must expose `await InterestingFactsExtractor.extract(text: str) -> str` as its supported execution interface. | Must | The module returns one explanation string per input text. |
| FR-3 | The module must support only `Language.NL` as the source language and `Language.RU` as the target language in V1, and must reject any other pair during extractor creation. | Must | Unsupported pair handling must fail fast. |
| FR-4 | The module must reject blank or whitespace-only input by raising `ValueError` rather than returning an empty explanatory result. | Must | Empty text is treated as invalid analysis input. |
| FR-5 | For single-word input, the explanation must identify the lexical item and its part of speech and must include morphology or inflection facts relevant to that part of speech. | Must | The module must adapt the explanation depth to lexical-item input. |
| FR-6 | For Dutch noun input, the explanation must state whether the noun takes `de` or `het`. | Must | This requirement is explicitly part of the requested interesting-facts contract. |
| FR-7 | For Dutch verb input, the explanation must include a conjugation set that covers singular and plural present-tense forms, including second-person plural, and must state whether the verb is regular or irregular when that distinction is relevant. | Must | The user explicitly called out verb-form coverage and second-person plural validation. |
| FR-8 | For compound lexical items, the explanation must identify the meaningful components and describe the composition in target-language explanatory prose. | Must | Compound decomposition is a required interesting-fact category. |
| FR-9 | For lexical-item input, the explanation must include at least one usage-oriented enrichment such as an example, a noteworthy usage note, or another concrete linguistic fact beyond bare translation. | Must | The module must return more than a minimal dictionary gloss. |
| FR-10 | For sentence input, the module must switch to sentence-analysis mode: it must segment the sentence into words or tokens, provide each item with a brief gloss or translation, and explain sentence construction, including major syntactic roles such as subject, predicate, and object when meaningful, plus relevant grammar such as tense or notable constructions. | Must | Sentence mode is intentionally lighter per token than lexical-item mode. |
| FR-11 | If the sentence represents a common expression, idiom, or widely used fixed phrase, the explanation must say so and describe that usage fact. | Must | Expression-level facts are part of the requested output. |
| FR-12 | The explanation prose must be written in the configured target language. | Must | The target language controls explanatory text, not the source language. |
| FR-13 | The returned explanation must contain only the requested analysis content and no assistant-style greetings, apologies, or conversational wrapper text. | Must | Callers receive display-ready output. |
| FR-14 | If the upstream model response cannot satisfy the mandatory content requirements for the applicable input mode, the module must treat the request as failed rather than returning partial analysis. | Must | No silent degradation or underspecified output is allowed. |
| FR-15 | Runtime failures during model invocation, response parsing, or mandatory-content validation must raise `APIError`. | Must | Callers need a stable typed failure contract. |
| FR-16 | For multi-sentence or otherwise longer text, the module should attempt best-effort processing instead of rejecting the request solely because it is longer than the primary V1 examples. | Should | V1 does not guarantee the same completeness or validation coverage for longer text as for lexical items and single sentences. |

### Rules and Invariants

- BR-1: The module does not detect the source language; it trusts the caller-provided language configuration.
- BR-2: Exactly one explanation string is returned for each successful input text.
- BR-3: Lexical-item mode and sentence mode are externally visible behavior modes; callers may rely on the documented distinction.
- BR-4: Sentence input must not be expanded into a full detailed lexical report for every token.
- BR-5: For parts of speech beyond nouns and verbs, the module may include relevant linguistic facts, but V1 does not guarantee part-of-speech-specific mandatory coverage beyond the documented noun and verb rules.
- BR-6: The module must fail fast on unsupported pairs, invalid input, and unusable responses; it must not fall back to another language, another mode, or partial output.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Reliability | Failures must be explicit and typed. | Unsupported pairs fail during initialization; runtime failures raise `APIError` | No fallback behavior is allowed. |
| NFR-2 | Usability | Successful output must be immediately readable by end users in the target language. | Explanatory prose is target-language text with source-language forms embedded only as linguistic data | The module is for explanation, not raw model output inspection. |
| NFR-3 | Packaging | Supported language-pair operation requires maintained module-provided instructions and examples. | Required prompt assets for each supported pair must be available at runtime | Missing required assets are contract-breaking. |
| NFR-4 | Quality | Mandatory linguistic facts must remain observable in output even though exact wording is not stable. | The contract must be testable by content presence rather than exact string equality | Supports flexible but enforceable tests. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Notes |
| --- | --- | --- | --- |
| FM-1 | An unsupported source/target language pair is requested. | Reject the request during extractor creation. | Caller must choose a supported pair. |
| FM-2 | Input is blank or whitespace-only. | Raise `ValueError`. | The module does not produce empty explanatory output for empty text. |
| FM-3 | The upstream model fails or returns unusable content. | Raise `APIError`. | The original failure should remain available as the cause. |
| FM-4 | Lexical-item analysis omits a mandatory fact such as article, conjugation coverage, or part-of-speech identification. | Treat the request as failed rather than returning partial analysis. | Mandatory facts depend on input shape and part of speech. |
| FM-5 | Sentence input contains no noteworthy grammar or idiom facts. | Return token glosses plus any remaining sentence-level observations that are still valid. | The module should not invent grammar facts when none are present. |
| FM-6 | Input contains multiple sentences or otherwise exceeds the primary V1 examples. | Attempt best-effort analysis without the full lexical-item or single-sentence completeness guarantees. | Longer text is allowed but not part of the strongly validated V1 contract. |

## 3. Public Contract

### Responsibilities and Boundaries

**Responsible For:**

- Producing target-language linguistic explanations for supported source texts.
- Switching between lexical-item mode and sentence-analysis mode based on the input text.
- Enforcing mandatory interesting-fact coverage for the applicable mode.
- Surfacing unsupported-pair and runtime failures explicitly.
- Attempting best-effort explanation for longer text without promoting it to a fully guaranteed V1 analysis mode.

**Not Responsible For:**

- Detecting the source language automatically.
- Persisting explanations or integrating with caches or databases.
- Returning a structured schema of linguistic facts in V1.
- Providing OCR, speech, or translation-only behavior as a substitute for explanation.
- Guaranteeing full analysis coverage for multi-sentence or paragraph-length text in V1.

### Public Interfaces

| ID | Interface Type | Direction | Counterparty | Contract Summary | Expected Behavior |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python class | Inbound | Application code and sibling packages | `from nl_processing.extract_interesting_facts.service import InterestingFactsExtractor` and then `InterestingFactsExtractor(source_language: Language, target_language: Language, model: str = "gpt-4.1-mini", service_tier: str | None = "priority")` | Creates a reusable explanation extractor for the supported language pair, uses the same first-version default model configuration as `translate_text`, and rejects unsupported pairs during construction. |
| IF-2 | Python async method | Inbound | `InterestingFactsExtractor` callers | `await extract(text: str) -> str` | Returns one target-language explanation string for valid input text or raises the documented failure type. |
| IF-3 | Data contract | Outbound | Callers consuming results | Plain `str` explanation output | Successful output is display-ready target-language prose containing the mandatory linguistic facts for the applicable input mode. |

Document all public contract surfaces here, including public classes, methods, functions, commands, endpoints, events, or other supported entry points.

### Internal and Non-Contract Notes

- Prompt wording, few-shot examples, internal validation heuristics, and any mode-classification helpers are internal only and are not part of the supported public API.
- Any module-private schemas or parsing helpers used to validate explanation completeness are internal implementation details.
- Any import path other than `nl_processing.extract_interesting_facts.service` should be treated as non-contract unless documented here later.

### External Dependencies and Constraints

| ID | Dependency or Constraint | Why It Matters | Behavioral Assumption or Limit | Notes |
| --- | --- | --- | --- | --- |
| EC-1 | Shared `Language` and `APIError` contracts from `nl_processing.core` | They define the caller-visible configuration and runtime failure shape. | Compatibility with those shared contracts is required. | This module does not redefine shared language or exception types. |
| EC-2 | Upstream OpenAI-backed model behavior | Non-empty explanation requests depend on an external LLM response. | Provider failures and unusable responses must surface explicitly. | No fallback provider behavior is assumed. |
| EC-3 | Module-provided pair-specific instruction assets and examples | The explanation contract depends on curated guidance for supported pairs. | Supported behavior is guaranteed only where valid module-provided assets exist. | The user explicitly requested prompt examples as part of the module design. |
| EC-4 | Source-language-specific linguistic conventions | Some mandatory facts depend on the source language, such as Dutch articles and Dutch verb forms. | Mandatory fact coverage may differ by supported source language. | V1 only supports Dutch source text. |

### Cross-Module Change References

| Affected Module | Why It Must Change | External Spec or Doc Reference | Ownership Status |
| --- | --- | --- | --- |
| N/A | No external module contract change is required for this new module spec. | N/A | N/A |

### Compatibility Notes

| ID | Area | Expectation | Impact if Broken | Notes |
| --- | --- | --- | --- | --- |
| COMP-1 | Public API shape | The documented constructor, including the `translate_text`-aligned default `model` and `service_tier` parameters, the import path, async `extract(text)` signature, and plain-string result remain stable for callers. | Callers may fail to import, instantiate, or consume the module correctly. | Returning structured data instead of `str` or changing the default config surface would be breaking. |
| COMP-2 | Mode semantics | Word/short-expression input continues to receive deeper lexical analysis, while sentence input continues to receive lighter token glosses plus sentence-level notes. | Callers and tests may receive materially different explanation shapes. | This distinction is part of the contract. |
| COMP-3 | Mandatory fact coverage | Dutch nouns continue to expose article facts and Dutch verbs continue to expose conjugation coverage including second-person plural. | Consumer expectations and high-level validation would break. | New languages may add requirements but must not remove documented ones silently. |
| COMP-4 | Explanation language | Explanatory prose remains in the configured target language. | End-user readability and downstream display assumptions would break. | Source-language tokens may still appear as analysis data. |
| COMP-5 | Longer text handling | Inputs longer than one sentence may be processed, but they do not gain the same guaranteed shape as lexical-item or single-sentence analysis in V1. | Callers could over-rely on behavior that is intentionally best-effort only. | This is an explicit non-guarantee, not a hidden limitation. |

## 4. Acceptance and Validation

### Acceptance Criteria

- AC-1: A caller can create `InterestingFactsExtractor` only for a supported language pair.
- AC-2: A supported Dutch noun input yields Russian explanatory prose that states the part of speech and includes `de` or `het`.
- AC-3: A supported Dutch verb input yields Russian explanatory prose that includes a present-tense conjugation set covering second-person plural and states regularity when relevant.
- AC-4: A compound lexical item yields Russian explanatory prose that identifies the meaningful parts of the compound.
- AC-5: A sentence input yields lighter token-level glosses plus sentence-level grammar, construction, or idiom notes rather than a full lexical dossier for each token.
- AC-6: Common expressions or idioms are identified explicitly when relevant.
- AC-7: Blank input raises `ValueError`, and unsupported language pairs fail fast during construction.
- AC-8: Runtime model or validation failures surface as `APIError`.
- AC-9: Multi-sentence input is not rejected solely for being longer than one sentence, but no fully guaranteed analysis shape is required in V1.

### High-Level Validation Coverage

| ID | Target | What Must Be True | Observable Evidence or Result |
| --- | --- | --- | --- |
| VAL-1 | FR-1, FR-2, IF-1, IF-2 | The documented import path, constructor, and async execution interface are usable by callers. | A caller can create the extractor for a supported pair and await `extract(text)`. |
| VAL-2 | FR-5, FR-6, FR-9 | Lexical-item mode returns a detailed explanation that includes part of speech, required noun/article facts where applicable, and at least one usage-oriented enrichment. | Observed output contains the analyzed word, part-of-speech identification, `de` or `het` for Dutch nouns, and an example or comparable usage note. |
| VAL-3 | FR-7 | Dutch verb analysis includes the required conjugation coverage. | Observed output contains a second-person plural verb form as part of a broader conjugation set and indicates regularity or irregularity when relevant. |
| VAL-4 | FR-8 | Compound lexical items are explained compositionally. | Observed output names meaningful components and describes the composition. |
| VAL-5 | FR-10, FR-11 | Sentence mode stays lighter per token while still explaining grammar or idiomatic usage when present. | Observed output includes token-level glosses plus sentence-level notes without expanding each token into a full standalone lexical report. |
| VAL-6 | FR-12, FR-13 | The explanation is target-language prose without assistant-style wrapper text. | Observed output is readable Russian explanatory text and contains no greeting, apology, or meta chatter. |
| VAL-7 | FR-14, FR-15 | Missing mandatory facts or upstream failures do not leak as partial success. | Caller receives `APIError` instead of incomplete explanation output. |
| VAL-8 | FR-3, FR-4 | Unsupported pairs and blank input fail before explanation generation. | Unsupported pairs fail during construction, and blank input raises `ValueError` instead of returning empty or fallback output. |
| VAL-9 | FR-16 | Longer text is not blanket-rejected only because it is longer than the core V1 examples. | A caller can submit multi-sentence input without a length-only rejection, while no deterministic content-shape assertion is required. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | The boundary between short expression and sentence may be ambiguous for some inputs. | Callers may see shape drift if the mode choice is inconsistent. | Keep the mode distinction explicit and validate representative borderline examples. |
| RISK-2 | Linguistic richness requirements can grow quickly across new source languages. | Adding languages without clear mandatory-fact rules could make the contract vague. | Add new language pairs only with language-specific mandatory-fact rules. |
| RISK-3 | Free-form explanation output can remain fluent while still omitting a required fact. | Weak validation could allow contract regressions. | Treat mandatory fact presence as a first-class validation requirement. |

### Open Questions

N/A. No unresolved contract questions remain for this revision.

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Approved | Promoted into explicit output contract | FR-2, IF-3, COMP-1 |
| RV-2 | A-2 | Approved with clarification | Promoted into explicit scope and best-effort boundary | Summary, Out of Scope, FR-16, FM-6, COMP-5 |
| RV-3 | A-3 | Approved | Promoted into explicit pair constraint | FR-3, EC-4 |
| RV-4 | A-4 | Approved from initial request | Promoted into explicit rule and boundary | BR-1 |
| RV-5 | OQ-1 | Approved as `ValueError` | Promoted into explicit invalid-input contract | FR-4, FM-2, AC-7, VAL-8 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-6 | OQ-1 | Resolved | Blank input must raise `ValueError` | FR-4, FM-2, AC-7, VAL-8 |

### Deferred Work

- D-1: Add additional source/target language pairs only through explicit contract expansion with language-specific mandatory-fact rules.
- D-2: Decide in a later revision whether longer text should remain best-effort only or become a fully guaranteed analysis mode.
- D-3: Decide whether a future structured output mode should complement or replace the plain-text explanation contract.
