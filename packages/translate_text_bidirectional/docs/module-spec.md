---
title: "translate_text_bidirectional Module Spec"
module_name: "translate_text_bidirectional"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
  - "../../translate_text/docs/module-spec.md"
---

# Module Spec: translate_text_bidirectional

## 1. Module Snapshot

### Summary

`translate_text_bidirectional` is a new developer-facing text translation module for `nl_processing`. It accepts the `nl <-> ru` pair at initialization and translates from whichever of those two languages the input text is written in into the other language. The module is prompt-led, uses multi-direction few-shot examples, and relies on model tool choice between two direction-specific tools instead of a caller-provided translation direction.

### Package and Documentation Location

**Python package path:**

- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/`

**Local module doc path:**

- `packages/translate_text_bidirectional/docs/module-spec.md`

**External references allowed:**

- `docs/module-spec.md`
- `packages/core/docs/module-spec.md`
- `packages/translate_text/docs/module-spec.md`

### System Context

The module sits beside `translate_text` as a sibling text-translation service. It serves callers that want one translator instance configured for a fixed language pair and do not want to decide direction before calling `translate(...)`. It depends on `core` for shared models, exceptions, and translation-chain setup, while owning its package-local prompt asset, direction-selection contract, and bidirectional regression cases.

### In Scope

- Public async text-translation service for the `nl <-> ru` pair.
- Constructor-time configuration of exactly two supported languages.
- Runtime direction selection based on whether the input is Dutch or Russian.
- Prompt-first design with one combined bidirectional prompt asset.
- Two internal model tools, one per direction, with model-decided tool choice.
- Reuse of existing `translate_text` test scenarios, adapted to verify both directions.

### Out of Scope

- Support for language pairs beyond `nl <-> ru` in v1.
- Caller-provided explicit direction selection in the public API.
- Automatic handling of languages outside the configured pair beyond returning `""`.
- Glossaries, terminology injection, caching, chunking, streaming, or persistence.
- Refactoring `translate_text` in place.
- Runtime fallbacks to sibling modules or alternate prompts.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | The combined few-shot prompt can teach reliable dominant-language inference for mixed NL/RU input without adding separate classifier logic. | Temporary Working Assumption | Kept explicit because mixed-input behavior remains in scope but is not a v1 acceptance gate. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `BidirectionalTextTranslator(source_language, target_language, model, service_tier)` and `await translate(text: str) -> str`. | Must | Public API stays close to `translate_text`, but direction is inferred internally. |
| FR-2 | V1 must accept only the configured `nl` and `ru` pair and reject any other pair during initialization. | Must | Initial scope is explicitly limited to Dutch and Russian. |
| FR-3 | For Dutch input, the module must return Russian translation text. | Must | One half of the bidirectional contract. |
| FR-4 | For Russian input, the module must return Dutch translation text. | Must | The other half of the bidirectional contract. |
| FR-5 | The module must preserve markdown structure such as headings, emphasis, lists, and paragraph breaks in both directions. | Must | Same quality bar as `translate_text`. |
| FR-6 | The public result must contain only the translated text and no conversational prefixes, explanations, or wrapper DTOs. | Must | Tool-calling remains internal. |
| FR-7 | Blank input must return `""` without invoking the model. | Must | Same short-circuit contract as `translate_text`. |
| FR-8 | Input that contains neither Dutch nor Russian must return `""`. | Must | Preserves the current `translate_text` behavior for unsupported content. |
| FR-9 | Mixed Dutch/Russian input must be translated according to the dominant supported language in the input. | Must | Kept in scope by user decision, but not part of v1 acceptance coverage. |
| FR-10 | Runtime invoke, tool-selection, tool-argument, prompt-loading, or parsing failures must be surfaced as `APIError`. | Must | Same typed runtime error contract as `translate_text`. |
| FR-11 | The module must use two direction-specific model tools and allow the model to choose which tool to call for each non-empty request. | Must | Core architectural requirement of the module. |
| FR-12 | Existing `translate_text` regression scenarios must be reused as seed cases and extended so the new suite verifies both `nl -> ru` and `ru -> nl` behavior. | Must | Keeps the new module anchored to the current quality baseline. |

### Rules and Invariants

- BR-1: The public result is always a plain `str`.
- BR-2: V1 supports only the unordered pair `nl <-> ru`.
- BR-3: Pair validation happens during service construction, not when translation starts.
- BR-4: Blank input never reaches the model.
- BR-5: Input outside the configured language pair returns `""` rather than a guessed translation.
- BR-6: Mixed-language input resolves to exactly one direction and must not trigger both tools.
- BR-7: The module must not expose a caller-controlled direction parameter in v1.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Text translation should remain interactive for typical short content. | <5s for a reviewed ~100-word case | Same bar as `translate_text`. |
| NFR-2 | Initialization | Service construction must stay lightweight. | No API calls during init | The constructor only validates the pair and builds the chain. |
| NFR-3 | Quality | Prompt behavior must be reviewable and repeatable for both directions. | Package-local generated prompt asset plus bidirectional regression tests | Prompt and few-shot examples are first-class assets. |
| NFR-4 | Compatibility | Extending shared chain-building in `core` must not regress one-way translation modules. | Existing one-way package tests remain green | Reuse is preferred, but compatibility is mandatory. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Unsupported language pair is requested at init. | Raise `ValueError`. | Add code, prompt assets, and tests together before claiming support. |
| FM-2 | Input is blank or whitespace-only. | Return `""` without invoking the model. | Valid empty-output path. |
| FM-3 | Input contains neither Dutch nor Russian. | Return `""`. | No fallback translation attempt. |
| FM-4 | Input mixes Dutch and Russian. | Translate according to the dominant supported language. | Prompt and few-shot examples must teach this rule; v1 does not gate it in acceptance. |
| FM-5 | The model fails to select a valid direction tool or returns invalid tool args. | Raise `APIError`. | Treat as runtime failure, not silent fallback. |
| FM-6 | Prompt, API, or parsing error occurs. | Raise `APIError`. | Caller can retry or surface the issue. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Bidirectional text translation behavior for the configured `nl <-> ru` pair.
- One combined prompt asset with instructions and examples for both directions.
- Two internal tool schemas, one for `nl -> ru` and one for `ru -> nl`.
- Runtime mapping from the selected tool output to a plain translated string.
- Bidirectional regression tests derived from the current `translate_text` package.

**Does Not Own:**

- Generic language detection services outside the configured pair.
- Caching, persistence, batching, chunking, or glossary management.
- Runtime fallback orchestration across alternate prompts or sibling modules.
- Low-level prompt deserialization and base chain composition that can live in `core`.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `BidirectionalTextTranslator(source_language, target_language, model, service_tier)` plus `await translate(text: str) -> str` | API shape stays close to `translate_text`, but direction is inferred internally. |
| IF-2 | Shared helper | Inbound | `core` | Extended translation-chain builder with prompt loading, pair validation, and multiple bound tools | Preferred reuse path rather than duplicating chain logic locally. |
| IF-3 | Asset/API | Outbound | Prompt assets + OpenAI | One combined prompt asset, likely `prompts/nl_ru_bidirectional.json`, plus two internal tool schemas bound on one chat model | Single asset teaches both directions and dominance rules. |
| IF-4 | Test contract | Inbound | Package test suites | Existing `translate_text` scenarios promoted into bidirectional unit, integration, and e2e cases | Ensures parity with the current one-way quality baseline. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Service instance state | Owned | Configured languages, normalized supported pair, and pre-built multi-tool chain. | Runtime only | No persistence. |
| Combined prompt asset | Owned | Bidirectional prompt instructions and few-shot examples for `nl <-> ru`. | Versioned with the package | Source of truth for direction selection and translation style. |
| Directional tool schemas | Owned | One internal schema per direction, each returning translated text. | Runtime only | Public API still returns plain `str`. |
| Pair normalization rule | Owned | Validation that constructor args represent the supported unordered pair regardless of argument order. | Runtime only | Keeps familiar argument names while removing source/target runtime semantics. |

### Processing Flow

1. The constructor receives `source_language` and `target_language`, validates that together they represent the supported unordered pair `nl <-> ru`, and rejects any other combination.
2. The constructor loads the combined bidirectional prompt asset and builds a multi-tool translation chain through shared `core` infrastructure.
3. `translate()` returns `""` immediately for blank input.
4. Non-empty text is wrapped as the request payload and sent through the async chain.
5. The model chooses exactly one of the two direction-specific tools based on the dominant supported language in the input.
6. The selected tool call is parsed into translated text and returned as a plain string.
7. Any invoke, tool-selection, tool-argument, prompt-loading, or parsing failure is wrapped as `APIError`.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep constructor parameter names `source_language` and `target_language` for API continuity, but normalize them as an unordered configured pair. | Decided | Preserves familiar call sites while matching bidirectional behavior. | Parameter names do not define runtime translation direction. |
| DEC-2 | Use one combined prompt asset for both directions instead of separate directional prompt files. | Decided | Direction choice and mixed-language guidance must be taught in one shared context. | Prompt maintenance is centralized but more complex. |
| DEC-3 | Bind two direction-specific tools on one model call and let the model choose the tool. | Decided | This is the requested mechanism for direction inference. | Tool-selection quality becomes part of the QA surface. |
| DEC-4 | Extend shared `core` translation-chain helpers to support multi-tool translation flows. | Decided | Avoids duplicating prompt loading and model setup patterns already used by `translate_text`. | `core` must grow without regressing one-way callers. |
| DEC-5 | Reuse existing `translate_text` tests as seed regression cases and mirror them in both directions. | Decided | Keeps the new module grounded in known prompt and QA patterns. | Test fixtures and assertions need explicit bidirectional expansion. |

### Consistency Rules

- CR-1: The configured pair is treated as unordered for validation; `NL,RU` and `RU,NL` must construct equivalent service instances.
- CR-2: Each non-empty request must produce exactly one selected translation tool call, never zero and never both.
- CR-3: Combined prompt assets and regression tests must be updated together whenever direction-selection behavior changes.
- CR-4: New `core` multi-tool helper behavior must remain compatible with existing one-way translation modules.
- CR-5: Any bidirectional example promoted into the prompt asset must remain represented in automated regression tests.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-1 | IF-1, DEC-1 | QA-1 |
| FR-2 | IF-1, DEC-1, CR-1 | QA-1 |
| FR-3 | IF-3, DEC-2, DEC-3, CR-2 | QA-2 |
| FR-4 | IF-3, DEC-2, DEC-3, CR-2 | QA-3 |
| FR-5 | IF-3, DEC-2, CR-3 | QA-4 |
| FR-6 | IF-3, DEC-3, CR-2 | QA-4 |
| FR-7 | Processing Flow step 3, BR-4 | QA-5 |
| FR-8 | IF-3, BR-5 | QA-6 |
| FR-9 | IF-3, DEC-2, DEC-3, BR-6 | Not gated in v1 acceptance; see RISK-3 and D-2 |
| FR-10 | IF-2, Processing Flow step 7 | QA-7 |
| FR-11 | IF-2, IF-3, DEC-3, DEC-4, CR-2 | QA-8 |
| FR-12 | IF-4, DEC-5, CR-3, CR-5 | QA-9 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: The module initializes successfully when configured with `nl` and `ru` in either constructor argument order, and rejects any other pair at construction time.
- AC-2: Dutch input produces non-empty Russian output with preserved markdown and no assistant chatter.
- AC-3: Russian input produces non-empty Dutch output with preserved markdown and no assistant chatter.
- AC-4: Blank input returns `""` without invoking the model.
- AC-5: Input containing neither Dutch nor Russian returns `""`.
- AC-6: Runtime invoke, tool-call, or parsing failures surface as `APIError`.
- AC-7: Existing `translate_text` regression scenarios are mirrored into bidirectional automated tests and pass in the new package.

### Testing Strategy

**Framework and Constraints:**

- Reuse the same package-local `pytest` structure as `translate_text`: `tests/unit`, `tests/integration`, and `tests/e2e`.
- Reuse the existing package `Makefile` pattern so local validation runs through `make check`.
- Reuse the current repo package-check flow: `ruff format`, `ruff check --fix`, `pylint` max-module-lines, `pylint` bad-builtin gate, unit tests locally, and integration/e2e tests in Doppler-backed environments.
- Keep the service async and test it through the same async `pytest` style already used in the current translation package.
- Do not add mixed-input coverage to the accepted v1 test matrix.

**Unit:**

- Constructor accepts the supported unordered `nl <-> ru` pair regardless of argument order.
- Constructor rejects unsupported pairs.
- Blank and whitespace-only input short-circuit to `""` without chain invocation.
- Runtime exceptions are wrapped as `APIError` while preserving the original cause.
- Multi-tool chain wiring is configured with both direction-specific tools.
- Service parsing accepts either valid direction tool result and still returns plain `str`.

**Integration:**

- Live API Dutch-to-Russian translation returns clean, non-empty output.
- Live API Russian-to-Dutch translation returns clean, non-empty output.
- Markdown preservation is verified in both directions.
- Output-script sanity checks are verified on direction-appropriate simple cases.
- Non-Dutch-or-Russian input returns `""`.
- Short-text latency remains within the same interactive bar as `translate_text`.

**Contract:**

- Combined prompt asset exists and is loadable.
- Shared `core` multi-tool translation-chain helper binds both tools and remains compatible with one-way callers.
- Exactly one tool result shape is accepted by the service per successful request.

**E2E or UI Workflow:**

- Mirror the existing full-markdown translation scenario in both directions.
- Mirror the existing short-sentence translation scenario in both directions.
- Mirror the existing hard quality or product-box style scenario in both directions using direction-appropriate expected key terms.
- Mirror the unsupported-pair initialization failure scenario.
- Keep these as hard e2e assertions rather than manual review checkpoints.

**Operational or Non-Functional:**

- Preserve the current short-text latency gate used by `translate_text`.
- Run the full package check flow in PR CI.
- Run root-level duplicate-code and dead-code gates in the repo-wide CI flow.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-1, FR-2 | Unit | Supported-pair normalization and unsupported-pair init tests | PR CI | Confirms unordered-pair constructor behavior. |
| QA-2 | FR-3 | Integration + E2E | Dutch-to-Russian clean output, markdown, and hard quality tests | PR CI / nightly | Mirrors existing one-way NL->RU cases. |
| QA-3 | FR-4 | Integration + E2E | Russian-to-Dutch clean output, markdown, and hard quality tests | PR CI / nightly | Reverse-direction parity gate. |
| QA-4 | FR-5, FR-6 | Integration | Chatter-free output and markdown preservation in both directions | PR CI / nightly | Protects the public output contract. |
| QA-5 | FR-7 | Unit | Blank or whitespace short-circuit tests with no chain invocation | PR CI | Same guardrail as `translate_text`. |
| QA-6 | FR-8 | Integration | Non-pair-language input returns `""` | PR CI / nightly | Keeps inherited behavior explicit. |
| QA-7 | FR-10 | Unit | `APIError` wrapping and cause-preservation tests | PR CI | Same runtime error contract as the current module. |
| QA-8 | FR-11 | Unit + Contract | Multi-tool helper binds both tools and service accepts exactly one valid tool result shape | PR CI | Verifies the new architectural mechanism without a bespoke harness. |
| QA-9 | FR-12 | E2E | Mirrored legacy regression cases remain present and passing in both directions | PR CI / nightly | Protects continuity with the current module's test corpus. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package `make check` flow | Enforce formatting, lint, file-size, and package test quality gates | Local / PR CI | Any `ruff`, `pylint`, or package test failure |
| SC-2 | Repo root `make check` flow | Enforce repo-wide dead-code and duplicate-code checks alongside per-package checks | PR CI | `vulture`, `jscpd`, or any package-check failure |
| SC-3 | Prompt asset load test | Ensure the combined bidirectional prompt asset remains present and deserializable | PR CI | Missing or malformed prompt JSON |
| SC-4 | Existing one-way translation package tests | Prevent multi-tool helper changes from regressing current translation callers | PR CI | Any regression in existing one-way packages |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| N/A | Manual verification is intentionally excluded from v1. Hard e2e assertions are required instead. | N/A | N/A |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | A single combined prompt may improve one direction while degrading the other. | Bidirectional quality can drift unevenly. | Keep mirrored hard integration and e2e coverage for both directions in the same change. |
| RISK-2 | Extending `core` for multi-tool chains may regress existing one-way translation modules. | Cross-package breakage outside the new module. | Add compatibility coverage for current one-way callers and keep helper changes minimal. |
| RISK-3 | Mixed-language dominant-direction behavior is in scope but is not a v1 acceptance gate. | The implementation may satisfy accepted tests while FR-9 remains weakly protected. | Keep the gap explicit, revisit after the first implementation, and add coverage in follow-up work if stable assertions are available. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should mixed-input dominant-language behavior become an acceptance-tested requirement in the first follow-up iteration? | Open | Revisit after the initial hard e2e suite lands | Current v1 keeps the behavior as a requirement without acceptance coverage. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | Proposed package path and doc location | Approved | Promoted into explicit package and doc locations | Module Snapshot |
| RV-2 | Public async `translate(text) -> str` API | Approved | Promoted into explicit requirement | FR-1 |
| RV-3 | Input outside Dutch or Russian returns `""` | Approved | Promoted into explicit requirement and rule | FR-8, BR-5 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-4 | Earlier question about mixed-input scope without v1 acceptance coverage | Resolved | Keep mixed-input dominant-language behavior as an explicit requirement, but do not make it a v1 acceptance gate | FR-9, RISK-3, D-2 |

### Deferred Work

- D-1: Support language pairs beyond `nl <-> ru`.
- D-2: Add stable automated acceptance coverage for mixed-input dominant-language behavior if a hard oracle becomes available.
- D-3: Add richer observability around tool-choice behavior if future debugging needs it.
