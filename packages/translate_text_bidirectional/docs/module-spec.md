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

`translate_text_bidirectional` is a new developer-facing text translation module for `nl_processing`. It accepts a configured source language and target language, currently limited to the `nl`/`ru` pair, and applies source-anchored runtime semantics: input in the configured source language is translated into the configured target language, while input in any other language is translated into the configured source language. The module is prompt-led, uses multi-direction few-shot examples, and relies on model tool choice between two direction-specific tools instead of a caller-provided translation direction.

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

The module sits beside `translate_text` as a sibling text-translation service. It serves callers that want one translator instance configured for a fixed source/target setup and do not want to decide direction before calling `translate(...)`. It depends on `core` for shared models, exceptions, and prompt/model utilities, while owning package-local chain building, prompt-led source-anchored direction selection, and bidirectional regression cases.

### In Scope

- Public async text-translation service for ordered `nl`/`ru` source-target configurations.
- Constructor-time configuration of the supported source language and target language.
- Runtime direction selection based on whether the input is in the configured source language.
- Prompt-first design with package-local prompt assets/examples and constructor-driven runtime prompt generation.
- Two internal model tools, one per direction, with model-decided tool choice.
- Reuse of existing `translate_text` test scenarios, adapted to verify both directions.

### Out of Scope

- Support for language values beyond `nl` and `ru` in v1.
- Caller-provided explicit direction selection in the public API.
- Runtime rejection of non-source input languages with `""`.
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
| FR-2 | V1 must accept only ordered configurations that use `nl` and `ru` as `source_language` and `target_language`, and reject any other initialization values. | Must | Initial scope stays limited to Dutch and Russian, but constructor order is now semantically meaningful. |
| FR-3 | If input text is in the configured source language, the module must return translation text in the configured target language. | Must | Source-anchored forward direction. |
| FR-4 | If input text is not in the configured source language, the module must return translation text in the configured source language. | Must | Reverse direction is keyed off source-language mismatch, not target-language membership. |
| FR-5 | The module must preserve markdown structure such as headings, emphasis, lists, and paragraph breaks in both directions. | Must | Same quality bar as `translate_text`. |
| FR-6 | The public result must contain only the translated text and no conversational prefixes, explanations, or wrapper DTOs. | Must | Tool-calling remains internal. |
| FR-7 | Blank input must return `""` without invoking the model. | Must | Same short-circuit contract as `translate_text`. |
| FR-8 | Blank-input short-circuit behavior must remain the only empty-string success path. | Must | Non-blank inputs are translated rather than rejected solely because they are not in the configured target language. |
| FR-9 | Mixed-language input must be translated according to the dominant language detected by the prompt-led contract: dominant configured-source input goes to the configured target, and any other dominant language goes to the configured source. | Must | Kept in scope by user decision, but not part of v1 acceptance coverage. |
| FR-10 | Runtime invoke, tool-selection, tool-argument, prompt-loading, or parsing failures must be surfaced as `APIError`. | Must | Same typed runtime error contract as `translate_text`. |
| FR-11 | The module must use two direction-specific model tools and allow the model to choose which tool to call for each non-empty request. | Must | Core architectural requirement of the module. |
| FR-12 | Existing `translate_text` regression scenarios must be reused as seed cases and extended so the new suite verifies both `nl -> ru` and `ru -> nl` behavior. | Must | Keeps the new module anchored to the current quality baseline. |

### Rules and Invariants

- BR-1: The public result is always a plain `str`.
- BR-2: V1 supports only ordered configurations composed of `nl` and `ru`.
- BR-3: Pair validation happens during service construction, not when translation starts.
- BR-4: Blank input never reaches the model.
- BR-5: Any non-blank input that is not in the configured source language is translated into the configured source language rather than rejected with `""`.
- BR-6: Mixed-language input resolves to exactly one direction and must not trigger both tools.
- BR-7: The module must not expose a caller-controlled direction parameter in v1.
- BR-8: Constructor parameter order defines runtime behavior; swapping `source_language` and `target_language` changes the contract.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Text translation should remain interactive for typical short content. | <5s for a reviewed ~100-word case | Same bar as `translate_text`. |
| NFR-2 | Initialization | Service construction must stay lightweight. | No API calls during init | The constructor only validates the pair and builds the chain. |
| NFR-3 | Quality | Prompt behavior must be reviewable and repeatable for both directions. | Package-local prompt generator, generated prompt asset, and bidirectional automated tests | Prompt assets and few-shot examples are first-class behavior inputs. |
| NFR-4 | Isolation | Bidirectional chain-building behavior must remain package-scoped. | No cross-module helper changes required for this module contract | Shared primitives may be reused, but package-local behavior owns the multi-tool flow. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Unsupported source/target configuration is requested at init. | Raise `ValueError`. | Add code, prompt assets, and tests together before claiming support. |
| FM-2 | Input is blank or whitespace-only. | Return `""` without invoking the model. | Valid empty-output path. |
| FM-3 | Input is non-blank and not in the configured source language, including English or any other language. | Translate into the configured source language. | No empty-output rejection for non-source text. |
| FM-4 | Input mixes languages. | Translate according to the dominant-language outcome produced by the prompt-led contract. | Prompt and few-shot examples must teach this rule; v1 does not gate it in acceptance. |
| FM-5 | The model fails to select a valid direction tool or returns invalid tool args. | Raise `APIError`. | Treat as runtime failure, not silent fallback. |
| FM-6 | Prompt, API, or parsing error occurs. | Raise `APIError`. | Caller can retry or surface the issue. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Bidirectional text translation behavior for ordered `nl`/`ru` source-target configurations.
- One combined prompt asset with instructions and examples for both directions.
- Two internal tool schemas, one for `nl -> ru` and one for `ru -> nl`.
- Runtime mapping from the selected tool output to a plain translated string.
- Bidirectional regression tests derived from the current `translate_text` package.

**Does Not Own:**

- Generic language detection services outside the configured pair.
- Caching, persistence, batching, chunking, or glossary management.
- Runtime fallback orchestration across alternate prompts or sibling modules.
- Cross-module multi-tool orchestration contracts outside this package.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `BidirectionalTextTranslator(source_language, target_language, model, service_tier)` plus `await translate(text: str) -> str` | API shape stays close to `translate_text`, but direction is inferred internally from source-anchored rules. |
| IF-2 | Shared primitives | Inbound | `core` | Shared models, `APIError`, and prompt/model utilities used by the package-local chain builder | Reuse stable primitives without requiring `core` to own bidirectional multi-tool assembly. |
| IF-3 | Asset/API | Outbound | Prompt assets + OpenAI | Package-local prompt generator and generated prompt asset, plus two internal tool schemas bound on one chat model | Constructor inputs drive the runtime prompt while keeping prompt assets/examples reviewable. |
| IF-4 | Test contract | Inbound | Package test suites | Existing `translate_text` scenarios promoted into bidirectional unit and e2e cases | Ensures parity with the current one-way quality baseline using the actual package-local coverage shape. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Service instance state | Owned | Configured source language, configured target language, and pre-built multi-tool chain. | Runtime only | No persistence. |
| Prompt generator and generated prompt asset | Owned | Package-local prompt instructions and few-shot examples for ordered `nl`/`ru` source-target behavior, with constructor-driven runtime prompt generation. | Versioned with the package | Source of truth for source-anchored direction selection and translation style. |
| Directional tool schemas | Owned | One internal schema per direction, each returning translated text. | Runtime only | Public API still returns plain `str`. |
| Source-target configuration rule | Owned | Validation that constructor args use only the currently supported `nl` and `ru` values and preserve caller-provided order. | Runtime only | Keeps parameter names semantically active in runtime behavior. |

### Processing Flow

1. The constructor receives `source_language` and `target_language`, validates that both values are within the supported `nl`/`ru` scope, preserves their order as runtime semantics, and rejects any unsupported configuration.
2. The constructor derives the runtime prompt from package-local prompt assets/examples and builds the multi-tool translation chain in this package using shared `core` primitives.
3. `translate()` returns `""` immediately for blank input.
4. Non-empty text is wrapped as the request payload and sent through the async chain.
5. The model chooses exactly one of the two direction-specific tools based on whether the prompt-led dominant-language outcome matches the configured source language.
6. The selected tool call is parsed into translated text and returned as a plain string.
7. Any invoke, tool-selection, tool-argument, prompt-loading, or parsing failure is wrapped as `APIError`.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep constructor parameter names `source_language` and `target_language` for API continuity and make them semantically authoritative for runtime direction selection. | Decided | Preserves familiar call sites while aligning public behavior with source-anchored semantics. | Swapping constructor args changes the contract and test expectations. |
| DEC-2 | Use one combined prompt asset for both directions instead of separate directional prompt files. | Decided | Direction choice and mixed-language guidance must be taught in one shared context. | Prompt maintenance is centralized but more complex. |
| DEC-3 | Bind two direction-specific tools on one model call and let the model choose the tool. | Decided | This is the requested mechanism for direction inference. | Tool-selection quality becomes part of the QA surface. |
| DEC-4 | Keep multi-tool chain building package-local while reusing stable `core` primitives. | Decided | The implemented module owns its source-anchored multi-tool flow and does not require a shared `core` extension to satisfy its contract. | Bidirectional behavior stays isolated to this package while still sharing common low-level utilities. |
| DEC-5 | Reuse existing `translate_text` tests as seed regression cases and mirror them in both directions. | Decided | Keeps the new module grounded in known prompt and QA patterns. | Test fixtures and assertions need explicit bidirectional expansion. |

### Consistency Rules

- CR-1: The configured source and target languages are treated as ordered; `source=nl,target=ru` and `source=ru,target=nl` are distinct valid configurations with different runtime behavior.
- CR-2: Each non-empty request must produce exactly one selected translation tool call, never zero and never both.
- CR-3: Combined prompt assets and regression tests must be updated together whenever direction-selection behavior changes.
- CR-4: Package-local prompt generation, tool binding, and response parsing must stay aligned with the same public contract.
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
| FR-8 | Processing Flow step 3, BR-4 | QA-5 |
| FR-9 | IF-3, DEC-2, DEC-3, BR-6 | Not gated in v1 acceptance; see RISK-3 and D-2 |
| FR-10 | IF-2, Processing Flow step 7 | QA-7 |
| FR-11 | IF-2, IF-3, DEC-3, DEC-4, CR-2 | QA-8 |
| FR-12 | IF-4, DEC-5, CR-3, CR-5 | QA-9 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: The module initializes successfully only with supported ordered `nl`/`ru` source-target configurations, preserves constructor order as public semantics, and rejects any other initialization values at construction time.
- AC-2: When configured with `source=nl` and `target=ru`, Dutch input produces non-empty Russian output with preserved markdown and no assistant chatter.
- AC-3: When configured with `source=nl` and `target=ru`, Russian input, English input, and other non-Dutch non-blank input produce non-empty Dutch output with preserved markdown and no assistant chatter.
- AC-4: Blank input returns `""` without invoking the model.
- AC-5: Non-blank input is never rejected with `""` solely because it is not in the configured target language.
- AC-6: Runtime invoke, tool-call, or parsing failures surface as `APIError`.
- AC-7: Existing `translate_text` regression scenarios are mirrored into bidirectional automated tests and pass in the new package.

### Testing Strategy

**Framework and Constraints:**

- Reuse the same package-local `pytest` style already used here: `tests/unit` and `tests/e2e`.
- Reuse the existing package `Makefile` pattern so local validation runs through `make check`.
- Reuse the current package-local check flow defined by the local `Makefile`, `ruff.toml`, `.jscpd.json`, and `vulture_whitelist.py`: `ruff format`, `ruff check --fix`, `pylint` max-module-lines, `pylint` bad-builtin gate, package-local `vulture`, package-local `jscpd`, and the package-local automated tests run through `make check`.
- Keep the service async and test it through the same async `pytest` style already used in the current translation package.
- Do not add mixed-input coverage to the accepted v1 test matrix.
- Keep e2e coverage comprehensive while using real API calls economically: when one live response can validate multiple behaviors, one test should assert all relevant qualities from that same response rather than splitting them across many separate API-backed cases.

**Unit:**

- Constructor accepts only supported ordered `nl`/`ru` configurations and preserves argument order as runtime semantics.
- Constructor rejects unsupported pairs.
- Blank and whitespace-only input short-circuit to `""` without chain invocation.
- Runtime exceptions are wrapped as `APIError` while preserving the original cause.
- Multi-tool chain wiring is configured with both direction-specific tools.
- Service parsing accepts either valid direction tool result and still returns plain `str`.

**E2E:**

- Live API source-language input translates to the configured target and returns clean, non-empty output.
- Live API non-source input translates to the configured source and returns clean, non-empty output.
- Markdown preservation is verified in both source-anchored directions.
- Output-script sanity checks are verified on direction-appropriate cases.
- Non-source language input is translated to the configured source language rather than rejected.
- Short-text latency remains within the same interactive bar as `translate_text`.

**Prompt and Tooling Contract:**

- Package-local prompt generator and generated prompt asset remain present and loadable.
- The package-local chain binds both direction-specific tools.
- Exactly one tool result shape is accepted by the service per successful request.

**E2E or UI Workflow:**

- Mirror the existing full-markdown translation scenario in both directions.
- Mirror the existing short-sentence translation scenario in both directions.
- Mirror the existing hard quality or product-box style scenario in both directions using direction-appropriate expected key terms.
- Mirror the unsupported-pair initialization failure scenario.
- Keep these as hard e2e assertions rather than manual review checkpoints.
- Prefer consolidated live assertions so one real API-backed response validates multiple relevant behaviors at once, such as direction correctness, markdown preservation, clean output, and key terminology.

**Operational or Non-Functional:**

- Preserve the current short-text latency gate used by `translate_text`.
- Run the full package check flow in PR CI.
- Run the package-local `make check` flow in PR CI.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-1, FR-2 | Unit | Supported ordered configuration and unsupported-init tests | PR CI | Confirms constructor-order semantics and initialization scope. |
| QA-2 | FR-3 | E2E | Source-language input to configured-target output with consolidated quality assertions | PR CI / nightly | Mirrors the forward source-anchored contract. |
| QA-3 | FR-4 | E2E | Non-source input to configured-source output with consolidated quality assertions | PR CI / nightly | Protects the expanded reverse-direction contract. |
| QA-4 | FR-5, FR-6 | E2E | Chatter-free output and markdown preservation in both directions | PR CI / nightly | Protects the public output contract. |
| QA-5 | FR-7 | Unit | Blank or whitespace short-circuit tests with no chain invocation | PR CI | Same guardrail as `translate_text`. |
| QA-6 | FR-8 | Unit + E2E | Blank-input short-circuit remains the only empty-string success path | PR CI / nightly | Keeps empty-output behavior narrow and explicit. |
| QA-7 | FR-10 | Unit | `APIError` wrapping and cause-preservation tests | PR CI | Same runtime error contract as the current module. |
| QA-8 | FR-11 | Unit + Contract | Package-local chain binds both tools and service accepts exactly one valid tool result shape | PR CI | Verifies the architectural mechanism without promising cross-module helper changes. |
| QA-9 | FR-12 | E2E | Mirrored legacy regression cases remain present and passing in both directions | PR CI / nightly | Protects continuity with the current module's test corpus. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package-local `make check` flow | Enforce formatting, lint, file-size, dead-code, duplication, and package test quality gates | Local / PR CI | Any `ruff`, `pylint`, `vulture`, `jscpd`, or package test failure |
| SC-2 | Prompt asset load test | Ensure the package-local prompt generator/assets remain present and deserializable | PR CI | Missing or malformed prompt resources |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| N/A | Manual verification is intentionally excluded from v1. Hard e2e assertions are required instead. | N/A | N/A |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | A single combined prompt may improve one direction while degrading the other. | Bidirectional quality can drift unevenly. | Keep mirrored hard e2e coverage for both source-anchored directions in the same change. |
| RISK-2 | Package-local prompt generation and tool wiring may drift from the intended source-anchored contract. | Direction selection can remain syntactically valid while behavior regresses. | Keep constructor-order, non-source-input, and mirrored bidirectional e2e coverage aligned with prompt changes. |
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
| RV-3 | Blank input returns `""` | Approved | Promoted into explicit requirement and rule | FR-8, BR-4 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-4 | Earlier question about mixed-input scope without v1 acceptance coverage | Resolved | Keep mixed-input dominant-language behavior as an explicit requirement, but do not make it a v1 acceptance gate | FR-9, RISK-3, D-2 |

### Deferred Work

- D-1: Support language values beyond `nl` and `ru`.
- D-2: Add stable automated acceptance coverage for mixed-input dominant-language behavior if a hard oracle becomes available.
- D-3: Add richer observability around tool-choice behavior if future debugging needs it.
