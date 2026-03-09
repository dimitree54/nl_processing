---
title: "extract_words_from_text Module Spec"
module_name: "extract_words_from_text"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
---

# Module Spec: extract_words_from_text

## 1. Module Snapshot

### Summary

`extract_words_from_text` extracts and normalizes lexical items from markdown text and returns a flat `list[Word]`. It uses prompt-driven LLM extraction instead of language-specific NLP code, which keeps the module small while allowing Dutch-specific normalization such as articles on nouns and infinitive verbs. The current shipped prompt set is Dutch-only.

### System Context

The module consumes plain text or markdown and produces normalized `core.models.Word` objects that downstream packages can filter, translate, or persist. It depends on `core` for models, prompt loading, and `APIError`, but owns the prompt instructions that define what normalization means.

### In Scope

- Public async `WordExtractor(language, model)` service.
- Markdown-transparent lexical extraction into `Word` objects.
- Prompt-defined normalization and flat `PartOfSpeech` tagging.
- Compound and multi-word expressions as single extracted units.
- Packaging of runtime prompt assets with the module.

### Out of Scope

- Image/OCR input or standalone language detection.
- Deterministic ordering or deduplication guarantees.
- Hardcoded per-language normalization logic in Python.
- Explicit support for languages without shipped prompt assets.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | The Dutch prompt remains the only shipped extraction prompt until more language assets and tests are added. | Needs Review | The current package ships `prompts/nl.json`. |
| A-2 | Prompt instructions remain the source of truth for normalization rules. | Needs Review | There is no language-specific post-processing in code. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `WordExtractor(language, model, reasoning_effort, temperature)` and `await extract(text: str) -> list[Word]`. | Must | Current defaults are `model="gpt-5-mini"`, `reasoning_effort="medium"`, `temperature=None`. |
| FR-2 | The extractor must ignore markdown syntax and return only lexical content in the target language. | Must | Markdown formatting is transparent to callers. |
| FR-3 | Each returned item must be a `Word` with `normalized_form`, `word_type`, and `language` populated. | Must | `language` is set programmatically by the service. |
| FR-4 | Compound expressions and multi-word phrases may be returned as single normalized entries. | Must | Prompt-driven behavior. |
| FR-5 | When no target-language words are found, the module should return `[]` rather than raising a domain-specific exception. | Must | Matches current contract and tests. |
| FR-6 | Upstream invoke or parsing failures must surface as `APIError`. | Must | Keeps failure handling typed for callers. |

### Rules and Invariants

- BR-1: Every result element is a `core.models.Word`.
- BR-2: `word_type` must be a valid `PartOfSpeech`; invalid tool output fails validation.
- BR-3: All returned words for one extractor instance share the same `language`.
- BR-4: Ordering and deduplication are not part of the public contract.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Extraction should stay within the current offline QA budget for short texts. | Product target <5s on ~100 words; current integration gate <180s | The offline `gpt-5-mini` profile is much slower than the previous lightweight model. |
| NFR-2 | Inference profile | Offline extraction should favor higher-quality reasoning over latency. | `model="gpt-5-mini"`, `reasoning_effort="medium"`, `temperature=None` | Current constructor behavior. |
| NFR-3 | Packaging | Prompt assets must be shipped with the package. | `prompts/nl.json` available at runtime | Covered by a packaging test. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Text contains no target-language words. | Return `[]`. | Caller can treat this as a valid empty extraction. |
| FM-2 | Prompt asset is missing or malformed. | Constructor fails during prompt load. | Add or repair the prompt asset before use. |
| FM-3 | API call, tool-call parsing, or schema validation fails. | Raise `APIError`. | Caller can retry or surface the failure. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Prompt-defined lexical extraction and normalization behavior.
- Mapping of LLM tool output into `Word` objects.
- Packaging and loading of extraction prompt assets.

**Does Not Own:**

- OCR/image input handling.
- Translation or persistence workflows.
- Shared enum/model definitions.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `await extract(text: str) -> list[Word]` | Main public interface. |
| IF-2 | Asset/API | Outbound | Prompt assets + OpenAI | `prompts/<language>.json`, `_WordList` tool schema, LangChain/OpenAI chain | Current shipped asset is Dutch only. |
| IF-3 | Shared contract | Inbound | `core` | `Language`, `PartOfSpeech`, `Word`, `APIError`, `load_prompt()` | Shared dependency surface. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Service instance state | Owned | Target language and pre-built chain. | Runtime only | No persistent state. |
| Prompt assets | Owned | Language-specific extraction instructions. | Versioned with the package | Define normalization behavior. |
| `Word` result mapping | Owned | Conversion from internal tool payload to shared DTOs. | Runtime only | Keeps public output consistent. |

### Processing Flow

1. The constructor picks the prompt JSON for `language`, loads it, and binds `_WordList` as the tool schema on `ChatOpenAI`.
2. `extract()` wraps the input text in a `HumanMessage` and invokes the async chain.
3. The first tool call is parsed into `_WordList`.
4. Each entry is converted into a shared `Word` with the extractor instance's target language.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep normalization logic in the prompt, not in Python post-processing. | Decided | Makes language support a prompt problem, not a custom NLP toolchain problem. | Prompt assets must stay synchronized with expected normalization rules. |
| DEC-2 | Use a flat shared `PartOfSpeech` taxonomy from `core`. | Decided | Keeps downstream filtering simple and type-safe. | Prompt outputs must match enum values exactly. |
| DEC-3 | Return `[]` rather than raising when the text lacks target-language words. | Decided | An empty extraction is a valid text-processing outcome. | Callers should not expect a domain error in this case. |
| DEC-4 | Validate quality with set-based comparisons instead of ordered equality. | Decided | LLM output order is not important to the workflow. | Tests focus on content completeness, not ordering. |

### Consistency Rules

- CR-1: Adding a new language requires a prompt asset plus tests; `Language` enum support alone is insufficient.
- CR-2: Prompt instructions and `PartOfSpeech` enum values must stay aligned.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, IF-2, DEC-1 | QA-1 |
| FR-3 | IF-3, DEC-2, CR-2 | QA-2 |
| FR-5 | DEC-3 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: Markdown input produces a flat `list[Word]` without leaking markdown syntax into the public contract.
- AC-2: Empty/non-target-language text returns `[]`, while API and parsing failures raise `APIError`.
- AC-3: Prompt assets remain packaged and the module continues to pass unit, integration, and e2e extraction tests.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest` suites under `tests/unit`, `tests/integration`, and `tests/e2e`.
- Treat live-API quality tests as the real acceptance signal for prompt behavior.

**Unit:**

- Constructor defaults, prompt loading failures, output mapping, and `APIError` wrapping.

**Integration:**

- Curated extraction quality cases, non-Dutch empty-result behavior, and latency budget checks.

**Contract:**

- Packaging test for prompt assets and schema-level `PartOfSpeech` validation.

**E2E or UI Workflow:**

- Pipeline-like text scenarios, including markdown and multi-word expressions.

**Operational or Non-Functional:**

- Static checks keep the module small, typed, and packageable.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Integration | Curated extraction-accuracy tests | PR CI / nightly | Validates markdown-transparent extraction. |
| QA-2 | FR-3 | Unit | Output mapping and enum-validation tests | PR CI | Protects typed `Word` output. |
| QA-3 | FR-5 | Integration | Non-target-language empty-result test | PR CI | Confirms the no-exception contract. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via package check | Preserve quality and packaging. | PR CI | Lint or dead-code failures. |
| SC-2 | Package tests | Preserve extraction behavior and prompt packaging. | PR CI | Unit/integration/e2e failures. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Normalization quality | Some lexical choices and normalization nuances are prompt-dependent. | Review extracted outputs for representative Dutch samples after prompt changes. | Reviewer notes plus sample outputs. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Performance expectations in docs and tests drift apart. | The module may appear to satisfy requirements that are not actually enforced. | Keep this spec aligned to the current automated gate and tighten tests deliberately. |
| RISK-2 | Unsupported languages currently fail through missing prompt assets rather than a clearer module-level error. | Callers may get implementation-shaped failures when exploring new languages. | Revisit the unsupported-language contract before expanding language support. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should the module introduce an explicit unsupported-language error instead of relying on prompt-file presence? | Open | Project owner to decide before adding another language | Current behavior is prompt-asset driven. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending language-expansion work | Revisit with the next new prompt asset |

### Deferred Work

- D-1: Add explicit unsupported-language errors if the package starts shipping more than one prompt.
- D-2: Tighten the automated latency gate if runtime stability improves.
