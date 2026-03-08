---
title: "translate_word Module Spec"
module_name: "translate_word"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
---

# Module Spec: translate_word

## 1. Module Snapshot

### Summary

`translate_word` translates batches of normalized Dutch words or short phrases into Russian and returns them as shared `Word` objects. It is designed to sit directly after `extract_words_from_text`, preserve input order, and process the whole batch in one LLM call. The current implementation supports only the `nl -> ru` pair and uses a pair-specific prompt asset plus the shared translation-chain builder from `core`.

### System Context

The module lives in the middle of the lexical pipeline between word extraction and downstream persistence. It depends on `core` for `Language`, `Word`, `PartOfSpeech`, `APIError`, and chain construction, and does not own any durable state or storage.

### In Scope

- Public async `WordTranslator(source_language, target_language, model)` interface.
- Batch translation of `list[Word]` into `list[Word]`.
- One-to-one order-preserving output contract.
- Pair-specific prompt asset and one-call batch translation behavior.

### Out of Scope

- Language pairs other than `nl -> ru`.
- Chunking or batching across multiple LLM calls.
- Deduplication, caching, or persistence.
- Extra output fields such as synonyms, examples, or alternative translations.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | The module continues using `Word` as both input and output rather than reintroducing a separate translation result type. | Needs Review | Matches current code and pipeline composition. |
| A-2 | One-to-one order-preserving mapping remains the core output contract for callers. | Needs Review | Tested today, but only partly enforced by prompt/schema behavior. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `WordTranslator(source_language, target_language, model)` and `await translate(words: list[Word]) -> list[Word]`. | Must | Current default model is `gpt-4.1-mini`. |
| FR-2 | The translator must return one output `Word` per input word in the same order. | Must | Public contract and existing tests. |
| FR-3 | The output `Word.language` must always be set programmatically to the target language. | Must | The LLM does not set this field directly. |
| FR-4 | Empty input must return `[]` without an API call. | Must | Explicit short-circuit in code. |
| FR-5 | Unsupported language pairs must be rejected during initialization. | Must | `_SUPPORTED_PAIRS` currently only allows `nl -> ru`. |
| FR-6 | Upstream invoke or parsing failures must be mapped to `APIError`. | Must | Typed failure contract. |

### Rules and Invariants

- BR-1: The public output type is always `list[Word]`.
- BR-2: The module currently supports only the `nl -> ru` pair.
- BR-3: Translation is performed in one LLM call for the full batch.
- BR-4: The module does not persist or cache translation results.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Batch translation should stay within the current real-API QA budget. | Current integration gate <10s for 10 words | Older docs targeted <1s; current enforced gate is looser. |
| NFR-2 | Structure | Output shape must stay machine-usable and order-preserving. | Typed tool schema + tests | Key integration property. |
| NFR-3 | Packaging | Pair-specific prompt assets must ship with the package. | `prompts/nl_ru.json` available at runtime | Required for init-time prompt load. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Unsupported pair is requested. | Raise `ValueError` at init. | Add support in code, prompts, and tests together. |
| FM-2 | Input list is empty. | Return `[]` immediately. | Valid no-op path. |
| FM-3 | Prompt, API, or parsing failure occurs. | Raise `APIError`. | Caller can retry or surface the problem. |
| FM-4 | The LLM returns the wrong number of items or low-quality translations. | Contract risk detected through tests/review. | Keep quality and mapping tests in place; consider explicit post-parse validation if needed. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Batch word translation prompt assets and schema.
- Mapping from internal tool output into shared `Word` results.
- Order-preserving, batch-oriented public translation API.

**Does Not Own:**

- Word extraction and normalization.
- Persistence, caching, or retry orchestration.
- Shared model or enum definitions.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `await translate(words: list[Word]) -> list[Word]` | Main public interface. |
| IF-2 | Shared helper | Inbound | `core` | `Language`, `Word`, `PartOfSpeech`, `APIError`, `build_translation_chain(...)` | Shared dependency surface. |
| IF-3 | Asset/API | Outbound | Prompt assets + OpenAI | `prompts/nl_ru.json`, `_TranslationBatch` tool schema, LangChain/OpenAI | Batch translation infrastructure. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Service instance state | Owned | Source language, target language, and pre-built chain. | Runtime only | No persistence. |
| Pair prompt asset | Owned | Prompt examples and instructions for `nl -> ru` word translation. | Versioned with the package | Main quality lever. |
| Output mapping logic | Owned | Conversion from internal tool entries to public `Word` results. | Runtime only | Sets `language` in code. |

### Processing Flow

1. The constructor validates the pair and builds the translation chain through `core.build_translation_chain(...)`.
2. `translate()` returns `[]` immediately if the input batch is empty.
3. Non-empty input words are joined by newline and sent as one `HumanMessage`.
4. The tool payload is parsed into `_TranslationBatch`, then mapped to target-language `Word` objects in the same sequence.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Use the shared `Word` model for both input and output. | Decided | Creates a seamless pipeline with `extract_words_from_text`. | Old docs referring to separate translation result objects are obsolete. |
| DEC-2 | Translate the full batch in one LLM call. | Decided | Minimizes cost and latency versus per-word calls. | Very large batches may require future chunking work. |
| DEC-3 | Keep target `language` assignment in code, not in the LLM payload. | Decided | Prevents schema ambiguity and keeps the public contract deterministic. | Output mapping remains package-owned logic. |
| DEC-4 | Keep one-to-one mapping as a contract, even though the LLM enforces it only indirectly today. | Decided | Downstream callers depend on positional correspondence. | Tests must continue guarding this behavior. |

### Consistency Rules

- CR-1: Pair support requires `_SUPPORTED_PAIRS`, prompt assets, and tests to change together.
- CR-2: Public examples and docs must remain async and use `Word`, not legacy translation wrapper types.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, DEC-2, DEC-4 | QA-1 |
| FR-3 | IF-2, DEC-3 | QA-2 |
| FR-5 | IF-3, DEC-1, CR-1 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `translate([])` returns `[]`, and supported non-empty batches return `Word` objects in input order.
- AC-2: Unsupported pairs fail during initialization, and invoke/parsing failures surface as `APIError`.
- AC-3: Prompt assets remain packaged and the module continues passing unit, integration, and e2e translation tests.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest` suites and live-API integration/e2e tests.
- Keep the one-to-one mapping guarantee explicitly covered in tests.

**Unit:**

- Constructor wiring, empty-input short-circuit, output mapping, and `APIError` wrapping.

**Integration:**

- Exact-match quality cases, one-to-one mapping checks, and the current latency budget for 10-word batches.

**Contract:**

- Prompt asset presence and unsupported-pair init behavior.

**E2E or UI Workflow:**

- Pipeline-like input batches and broader quality scenarios such as product-box vocabulary.

**Operational or Non-Functional:**

- Manual review when prompt examples or default model selection change materially.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Integration | One-to-one mapping and exact-match translation tests | PR CI / nightly | Protects positional correspondence. |
| QA-2 | FR-3 | Unit | Output-model mapping tests | PR CI | Confirms target language and type fields are set in code. |
| QA-3 | FR-5 | Unit | Unsupported-pair init tests | PR CI | Fail-fast guardrail. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via package check | Preserve package quality and packaging. | PR CI | Lint or dead-code failures. |
| SC-2 | Package tests | Preserve mapping, quality, and packaging behavior. | PR CI | Unit/integration/e2e failures. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Translation adequacy for ambiguous words | Exact-match tests use simple words and do not cover all semantic ambiguity. | Review representative outputs when prompt examples or models change. | Reviewer notes and example batches. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | The one-to-one mapping contract is not explicitly revalidated after parsing in production code. | A malformed LLM response could slip through until tests catch it. | Consider explicit length validation if this becomes an observed failure mode. |
| RISK-2 | Historical docs drifted away from the real contract (`Word` output, async API, current model/perf gate). | Consumers may copy outdated usage or targets. | Treat this spec and current tests as canonical. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should the module add explicit post-parse validation that `len(output) == len(input)`? | Open | Project owner to decide after observing real failures | Today this is enforced indirectly via prompt/schema/tests. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending future hardening of the parsing contract | Revisit if malformed batch outputs are observed |

### Deferred Work

- D-1: Add explicit output-length validation if indirect prompt/schema enforcement proves insufficient.
- D-2: Revisit chunking only if batch sizes grow beyond the current single-call assumption.
