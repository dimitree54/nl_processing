---
title: "Execution Task: Source-Anchored Bidirectional Semantics"
document_type: "task"
module: "translate_text_bidirectional"
source_spec: "../module-spec.md"
---

# Source-Anchored Bidirectional Semantics

## Objective

Implement the updated module-spec contract in `translate_text_bidirectional`: if input is in the configured `source_language`, translate to `target_language`; otherwise translate to `source_language`. Preserve the blank-input short circuit. Remove the old reverse-direction restriction that only configured-target-language input may translate back.

This is a contract change. Constructor argument order is now semantically meaningful: `source_language=Language.NL, target_language=Language.RU` and `source_language=Language.RU, target_language=Language.NL` are both valid but define different runtime behavior.

## Required Context

### Specs and docs to read first

- `docs/module-spec.md`

### Code and tests to read first

- `src/nl_processing/translate_text_bidirectional/service.py`
- `src/nl_processing/translate_text_bidirectional/prompts/generate_nl_ru_bidirectional_prompt.py`
- `src/nl_processing/translate_text_bidirectional/prompts/nl_ru_bidirectional.json`
- `tests/conftest.py`
- `tests/unit/translate_text_bidirectional/conftest.py`
- `tests/unit/translate_text_bidirectional/test_bidirectional_translator.py`
- `tests/unit/translate_text_bidirectional/test_error_handling.py`
- `tests/e2e/translate_text_bidirectional/assertions.py`
- `tests/e2e/translate_text_bidirectional/test_nl_to_ru_quality.py`
- `tests/e2e/translate_text_bidirectional/test_ru_to_nl_quality.py`
- `tests/e2e/translate_text_bidirectional/test_product_box_quality.py`
- `Makefile`

### Relevant skills
- `prompt_engineering` — recommended before editing prompt instructions and few-shot examples because behavior is prompt-led and direction selection depends on prompt quality.

## Scope

### In scope

- Update runtime semantics in this package to match the source-anchored module spec.
- Update prompt instructions, prompt examples, and generated prompt artifacts so they teach the new routing rule.
- Update unit and E2E coverage for the new contract.
- Keep package validation green under `make check`.

### Out of scope

- Any docs changes outside this task file and the already-updated `docs/module-spec.md`.
- New language-pair support beyond `nl` and `ru`.
- Mixed-language acceptance expansion beyond what the current spec already requires.
- Changes in other modules unless the user explicitly opens that scope.

## File-Scope Guidance For Dev

- Stay inside `packages/translate_text_bidirectional/`.
- Do not update any docs besides this task file and do not create additional planning files.
- Prefer package-local changes; do not move this contract into another package unless the user explicitly approves cross-module work.
- Keep every touched file below the repo file-size gate; decompose instead of compacting.

## Current-State Gap To Close

- `service.py` currently validates an unordered `nl`/`ru` pair and returns whichever tool payload comes back, but it does not explicitly encode the new semantic importance of constructor order.
- The prompt generator still teaches `"if Dutch then RU, if Russian then NL"` and explicitly teaches empty-string output for non-NL/RU text. That contradicts the new contract because non-source, non-blank text must now translate into the configured source language.
- Existing E2E coverage still contains the old behavior check that English input returns `""`.
- Existing tests prove both tool result shapes can be parsed, but they do not fully lock in the new semantic rule that non-source input, including non-target language input, must translate to source.

## Dependencies And Constraints

- Public contract source of truth: `docs/module-spec.md`.
- Runtime dependencies already in use: `langchain_core`, `langchain_openai`, `pydantic`, shared `Language` and `APIError` from `nl_processing.core`.
- Prompt source of truth: `src/nl_processing/translate_text_bidirectional/prompts/generate_nl_ru_bidirectional_prompt.py`.
- Generated prompt artifact: `src/nl_processing/translate_text_bidirectional/prompts/nl_ru_bidirectional.json` must be regenerated if the generator changes.
- Quality gate: `make check` runs lint, unit tests, and Doppler-backed E2E tests; all must be green unless a pre-existing unrelated failure is discovered.

## Implementation Workstreams

### 1. Align the runtime contract in `service.py`
- Make the constructor semantics explicit in code and tests: order matters because `source_language` defines the language that keeps forward translation, while all non-source input routes to source.
- Preserve support for the two valid ordered configurations that use `nl` and `ru`.
- Keep blank and whitespace-only input as the only success path that returns `""` without model invocation.
- Keep `APIError` wrapping for runtime failures.
- If the service relies on tool names or tool order implicitly, make that mapping explicit enough that the source-anchored contract is readable and testable.

### 2. Update prompt instructions and few-shot examples
- Rewrite the system instruction to teach this exact rule:
  - when dominant input language equals configured source language, translate to configured target;
  - otherwise translate to configured source language.
- Remove the old instruction/example that says non-NL/RU text should produce an empty string.
- Add or replace few-shot coverage so the prompt demonstrates at least:
  - source-language forward translation;
  - configured-target reverse translation back to source;
  - non-source and non-target language input translating into the configured source language;
  - blank input remaining empty.
- Keep markdown-preservation and no-chatter instructions.
- Regenerate `src/nl_processing/translate_text_bidirectional/prompts/nl_ru_bidirectional.json` from the generator after updating the source script.

### 3. Update unit tests for semantic routing
- Extend `tests/unit/translate_text_bidirectional/test_bidirectional_translator.py` so the suite proves constructor order is contract-significant, not just valid.
- Add unit coverage that non-source input does not short-circuit to `""` and instead returns the parsed translation payload.
- Add unit coverage for both ordered constructors:
  - `source=NL,target=RU`: NL input -> RU, RU input -> NL, EN input -> NL.
  - `source=RU,target=NL`: RU input -> NL, NL input -> RU, EN input -> RU.
- Keep blank and whitespace tests asserting no chain invocation.
- Keep error-handling tests in `tests/unit/translate_text_bidirectional/test_error_handling.py` green; extend only if runtime parsing assumptions changed.

### 4. Update E2E coverage with economical API usage
- Replace the old English-input-empty test in `tests/e2e/translate_text_bidirectional/test_nl_to_ru_quality.py` with a live case that proves non-source/non-target input translates into Dutch when configured as `source=NL,target=RU`.
- Add at least one live non-source/non-target-language case to the E2E suite. Use English unless there is a stronger existing fixture; assert Dutch output characteristics, not empty-string behavior.
- Keep live-call count low by making each live response validate multiple behaviors at once:
  - direction correctness;
  - no chatter;
  - non-empty output;
  - language/script sanity;
  - markdown preservation where applicable;
  - latency where already gated.
- Reuse the existing consolidated feature-matrix style instead of splitting one behavior across many separate API-backed tests.
- Keep product-box and markdown scenarios aligned with the new routing rule; update constructor configuration or assertions only where needed.

### 5. Final package validation
- Run the package-local validation flow from `Makefile` and resolve all introduced issues.
- Confirm prompt source and generated prompt artifact stay in sync.

## API / Library Notes For Implementation

### LangChain tool-calling prompt asset flow
- Current generator pattern is in `src/nl_processing/translate_text_bidirectional/prompts/generate_nl_ru_bidirectional_prompt.py`:

```python
return ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_INSTRUCTION),
    HumanMessage(content=EXAMPLE_INPUT),
    _make_example_ai(EXAMPLE_OUTPUT, "call_example", TOOL_NAME),
    ToolMessage(content=EXAMPLE_OUTPUT, tool_call_id="call_example"),
    MessagesPlaceholder(variable_name="text"),
])
```

- Keep using the same few-shot structure: `HumanMessage` -> `AIMessage` with `tool_calls` -> `ToolMessage`.
- Source: existing package code in `src/nl_processing/translate_text_bidirectional/prompts/generate_nl_ru_bidirectional_prompt.py`.

### Bound-tool invocation parsing
- Current service expects a LangChain response with `tool_calls[0]["args"]["text"]`:

```python
response = await self._chain.ainvoke({"text": [HumanMessage(content=text)]})
result_text = response.tool_calls[0]["args"]["text"]
```

- Preserve compatibility with this response shape unless there is a strong package-local reason to tighten validation.
- Source: existing package code in `src/nl_processing/translate_text_bidirectional/service.py`.

## Expected Files To Change

- `src/nl_processing/translate_text_bidirectional/service.py`
- `src/nl_processing/translate_text_bidirectional/prompts/generate_nl_ru_bidirectional_prompt.py`
- `src/nl_processing/translate_text_bidirectional/prompts/nl_ru_bidirectional.json`
- `tests/unit/translate_text_bidirectional/test_bidirectional_translator.py`
- `tests/unit/translate_text_bidirectional/test_error_handling.py` if needed to reflect any parsing-contract tightening
- `tests/e2e/translate_text_bidirectional/test_nl_to_ru_quality.py`
- `tests/e2e/translate_text_bidirectional/test_ru_to_nl_quality.py` if constructor-order semantics need to be exercised explicitly there
- `tests/e2e/translate_text_bidirectional/test_product_box_quality.py` if assertions or fixture routing need adjustment

## Acceptance Criteria

- The package behavior matches `docs/module-spec.md`: source-language input translates to target language; any other non-blank input translates to source language.
- Constructor argument order is observably semantic and covered by automated tests.
- Blank and whitespace-only input still return `""` without calling the model.
- Reverse-direction translation is no longer limited to only configured-target-language input.
- Prompt instructions, few-shot examples, and generated prompt artifact all reflect the same source-anchored rule.
- Automated tests include at least one non-source/non-target-language live E2E case and assert translated output into the configured source language.
- Live E2E coverage follows the economical-call philosophy: each real API response should validate multiple relevant behaviors instead of using one live call per micro-assertion.
- `make check` is green for this package.
- No docs are changed beyond the already-updated module spec and this task file.

## Verification Plan

- Run targeted unit tests first for fast feedback on constructor semantics, blank-input short circuit, and non-source routing.
- Run the package E2E suite with Doppler-backed credentials.
- Ensure the live suite contains a minimal but sufficient set of calls, with each live call asserting multiple behaviors.
- Run full package validation with `make check`.
- Manually inspect the prompt generator and generated JSON only to confirm they are synchronized; do not leave the artifact stale.

## Risks And Watchouts

- Prompt drift risk: changing reverse-direction semantics in the generator but not regenerating the JSON artifact will leave runtime behavior stale.
- Semantic mismatch risk: tests can accidentally keep proving only `NL <-> RU` routing while missing the broader rule that non-source, non-target input must route to source.
- Over-testing risk: adding many single-purpose live tests would violate the requested economical API-call strategy.
- Contract regression risk: preserving the old `""` behavior for English input would directly violate the updated spec.

## Blocking Conditions To Surface Immediately

- Stop and report if implementation appears to require code changes outside `packages/translate_text_bidirectional/`; this task is package-scoped.
- Stop and report if `docs/module-spec.md` and actual desired behavior appear to diverge again.
- Stop and report any pre-existing `make check` failure that is unrelated to this task and prevents a clean handoff.
