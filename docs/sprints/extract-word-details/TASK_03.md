---
Task ID: T3
Title: Implement `WordDetailsExtractor` service + unit/integration/e2e tests
Sprint: 2026-03-13_extract-word-details
Module: extract_word_details
Depends on: T2
Parallelizable: yes, with T4
---

## Goal / value

After this task, `WordDetailsExtractor` is fully implemented: it accepts `list[Word]`, validates the language pair, splits by POS, dispatches to POS-specific prompts via LangChain+OpenAI, parses typed results, skips unsupported POS with warnings, and returns `list[DetailedWordRecord]` in supported-input order. Unit, integration, and e2e tests verify the full contract. `make check` passes.

## Context (contract mapping)

- Module spec: `packages/extract_word_details/docs/module-spec.md` — FR-1 (public API), FR-2 (nl->ru only), FR-3 (empty input), FR-4 (single language, POS-based routing), FR-7 (skip unsupported POS), FR-11 (malformed LLM output fails fast), DEC-3 (batches split by POS), DEC-6 (skip with warning)
- Pattern reference: `packages/translate_word/src/nl_processing/translate_word/service.py`

## Preconditions

- T1 complete: schema registry, serializer, base models
- T2 complete: all 13 POS models registered, prompt assets generated

## Non-goals

- Database persistence (T4)
- Cache layer (T5)
- Supporting language pairs beyond NL->RU

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `packages/extract_word_details/` — source code and tests

**FORBIDDEN — this task must NEVER touch:**

- `packages/core/`, `packages/database/`, `packages/database_cache/`, or any other package
- Root configs

**Test scope:**

- Tests go in: `packages/extract_word_details/tests/unit/`, `tests/integration/`, `tests/e2e/`
- Test command: `make check` in `packages/extract_word_details/`

## Touched surface (expected files / modules)

**New files to create:**

- `src/nl_processing/extract_word_details/service.py` — `WordDetailsExtractor` class
- `src/nl_processing/extract_word_details/_pos_dispatch.py` — POS dispatch logic (group words by POS, load prompt+chain per POS)
- `src/nl_processing/extract_word_details/logging.py` — module logger setup
- `tests/unit/extract_word_details/test_service.py` — unit tests with mocked LLM
- `tests/unit/extract_word_details/test_pos_dispatch.py` — unit tests for POS grouping and dispatch
- `tests/integration/__init__.py`
- `tests/integration/extract_word_details/__init__.py`
- `tests/integration/extract_word_details/test_live_extraction.py` — live OpenAI extraction tests
- `tests/e2e/__init__.py`
- `tests/e2e/extract_word_details/__init__.py`
- `tests/e2e/extract_word_details/test_mixed_pos.py` — full mixed-POS extraction e2e

## Dependencies and sequencing notes

- Depends on T2 for POS models and prompt assets
- Can run in parallel with T4 (database changes)
- T5 (cache) does not depend on this directly — it depends on T4

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-core` v0.3
  - **Relevant docs**: https://python.langchain.com/docs/concepts/runnables/
  - **API**: `RunnableSerializable.ainvoke()` — async invocation of the prompt|llm chain
  - **Usage**: Same pattern as `translate_word`: `chain = prompt | llm`, then `response = await chain.ainvoke({"text": [HumanMessage(content=...)]})`. Extract tool calls from `response.tool_calls[0]["args"]`.
  - **Gotcha**: `response.tool_calls` may be empty if the LLM doesn't produce a tool call — must fail fast in that case.

- **Library**: `langchain-openai` v0.3
  - **Relevant docs**: https://python.langchain.com/docs/integrations/chat/openai/
  - **API**: `ChatOpenAI(model=..., temperature=..., reasoning_effort=...).bind_tools([schema], tool_choice=schema.__name__)`
  - **Usage**: Each POS gets its own chain with its own batch wrapper model bound as a tool.

- **Core helper**: `nl_processing.core.prompts.build_translation_chain()`
  - **Usage**: Reuse to build per-POS chains. Pass the POS-specific batch wrapper as `tool_schema`, the POS-specific prompt JSON path, and `_SUPPORTED_PAIRS`.
  - **Note**: Each POS produces a separate chain. The extractor maintains a dict of `{PartOfSpeech: chain}`.

- **Core exception**: `nl_processing.core.exceptions.APIError`
  - **Usage**: Wrap LLM failures in `APIError`, same as `translate_word`.

## Implementation steps (developer-facing)

1. **Create `logging.py`**:
   ```python
   import logging
   def get_logger(name: str) -> logging.Logger:
       return logging.getLogger(f"nl_processing.extract_word_details.{name}")
   ```

2. **Implement `_pos_dispatch.py`**:
   - `group_words_by_pos(words: list[Word]) -> dict[PartOfSpeech, list[tuple[int, Word]]]` — returns mapping of POS to (original_index, word) tuples
   - `get_supported_pos() -> set[PartOfSpeech]` — returns the set of POS values that have registered models in the schema registry
   - `split_supported_unsupported(words: list[Word], supported: set[PartOfSpeech]) -> tuple[list[tuple[int, Word]], list[tuple[int, Word]]]` — split into supported (with original indices) and unsupported

3. **Implement `service.py` — `WordDetailsExtractor`**:

   Constructor (`__init__`):
   - Parameters: `source_language: Language`, `target_language: Language`, `model: str = "gpt-5-mini"`, `reasoning_effort: str | None = "medium"`, `temperature: float | None = None`
   - Validate pair is in `_SUPPORTED_PAIRS = {("nl", "ru")}` — raise `ValueError` if not (FR-2)
   - Load the POS registry for this pair
   - Build a chain for each supported POS using `build_translation_chain()` with the POS-specific batch wrapper and prompt JSON

   `extract(words: list[Word]) -> list[DetailedWordRecord]`:
   - If `words` is empty, return `[]` (FR-3)
   - Validate all words have the same `language` matching `source_language` — raise `ValueError` if mixed (FR-4)
   - Split into supported and unsupported POS. Log warnings for each unsupported word (FR-7, DEC-6)
   - Group supported words by POS (DEC-3)
   - For each POS group:
     - Build the input text (newline-joined normalized forms)
     - Invoke the POS-specific chain: `response = await chain.ainvoke({"text": [HumanMessage(content=word_text)]})`
     - Parse the response: extract `response.tool_calls[0]["args"]`, validate with the batch wrapper model
     - If `tool_calls` is empty or validation fails, raise `APIError` (FR-11)
     - For each parsed entry, construct a `DetailedWordRecord` with `source_word`, `word_type`, `schema_key`, `schema_version`, and `payload` (serialized from the POS model)
   - Merge results back in original supported-input order (BR-4)
   - Return the merged list

   **`DetailedWordRecord` construction**: Import from `nl_processing.database.detailed_models`. Wait — that creates a dependency on `database`. Instead, since the `DetailedWordRecord` is defined in `database` and the extractor must return it (per the `DetailedWordExtractorPort` protocol in `database`), this means `extract_word_details` must depend on `database` for this type. BUT: `database` depends on `extract_word_details` for the extractor port. This is a circular dependency.

   **Resolution**: `DetailedWordRecord` is a simple Pydantic model with no database-specific logic. The correct approach: `extract_word_details` defines its own output type that matches the `DetailedWordRecord` shape. The `database` module's `DetailedWordExtractorPort` protocol already uses duck typing (it's a `Protocol`), so as long as the returned objects have the same fields, they satisfy the protocol. Actually, looking at the code, `DetailedWordExtractorPort` returns `list[DetailedWordRecord]` where `DetailedWordRecord` is imported from `database`. So the extractor must either:
   (a) Depend on `database` for the `DetailedWordRecord` type, or
   (b) Return objects that the caller wraps into `DetailedWordRecord`

   Looking at the `pyproject.toml` dependencies for `extract_word_details`: the spec says dependencies are `nl-processing-core`, `langchain-core`, `langchain-openai`, `pydantic`. NOT `nl-processing-database`.

   **Best approach**: Define a `DetailedWordRecord` in `extract_word_details` itself that has the same fields. The `database` port protocol uses structural typing (Protocol), and Pydantic models with the same fields are compatible. OR — move `DetailedWordRecord` to `core`. Since `core` is a shared dependency, this would be the cleanest. But the sprint rules say FORBIDDEN to touch `packages/core/`.

   **Practical approach**: `extract_word_details` defines its own `DetailedWordRecord` in its package. The `database` module already has its own. They share the same shape. Since `DetailedWordExtractorPort` uses `Protocol` and the return type annotation references `database.DetailedWordRecord`, the actual runtime duck-typing still works as long as the fields match. If strict type checking is needed, the integration layer (caller) can construct `database.DetailedWordRecord` from the extractor's output. This is an implementation detail the dev resolves at coding time.

   **SIMPLEST approach that avoids circular deps**: Add `nl-processing-database` as a dependency of `extract_word_details`. The `database` package has `detailed_models.py` with `DetailedWordRecord`, `detailed_ports.py` with `DetailedWordExtractorPort`, and `detailed_exceptions.py`. The `database` package does NOT depend on `extract_word_details` — it depends on the extractor through the protocol (duck typing, injected). So there's no circular dependency. `extract_word_details` → depends on → `database` (for the output type). `database` → optionally injects → an extractor that satisfies `DetailedWordExtractorPort`. This is one-way. DO this approach.

4. **Update `pyproject.toml`** to add `nl-processing-database` as a dependency and update `[tool.uv.sources]` to include `nl-processing-database = { path = "../database" }`.

5. **Update `Makefile` PACKAGE_PYTHONPATH** to include `../database/src` so that `nl_processing.database.detailed_models` is importable during tests:
   ```
   PACKAGE_PYTHONPATH=src:../core/src:../database/src
   ```

6. **Write unit tests (`test_service.py`)**:
   - Test `WordDetailsExtractor.__init__` with unsupported pair raises `ValueError`
   - Test `extract([])` returns `[]` without LLM call
   - Test `extract(words)` with mixed languages raises `ValueError`
   - Test `extract(words)` with unsupported POS logs warning and skips
   - Test `extract(words)` with supported POS — mock the chain to return a fake tool call response, verify `DetailedWordRecord` construction
   - Test `extract(words)` with empty tool_calls from LLM raises `APIError`
   - Test ordering: input [noun, verb, noun] → output in same order

7. **Write unit tests (`test_pos_dispatch.py`)**:
   - Test `group_words_by_pos` with mixed POS
   - Test `split_supported_unsupported` with some supported, some not

8. **Write integration tests (`test_live_extraction.py`)**:
   - Test live extraction for one representative word per POS (e.g., "hond" for noun, "lopen" for verb)
   - Verify returned `DetailedWordRecord` has valid `schema_key`, `schema_version`, and `payload` that round-trips through the serializer
   - These tests run under `doppler run --` for OpenAI API credentials

9. **Write e2e tests (`test_mixed_pos.py`)**:
   - Test mixed-POS extraction: pass a batch with noun, verb, adjective, phrase
   - Verify result count matches supported inputs
   - Verify result ordering
   - Verify each result has valid typed payload

10. **Verify**: Run `make check` in `packages/extract_word_details/`. All tests pass.

## Production safety constraints (mandatory)

- **Database operations**: None. The extractor does not persist anything.
- **API calls**: Integration/e2e tests call OpenAI API using test credentials from Doppler. No production API keys are used.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuse `build_translation_chain()` from core. Reuse `DetailedWordRecord` from database. Reuse schema registry from T1. Reuse POS models from T2.
- **Correct libraries only**: Same versions as existing packages.
- **No regressions**: New code only. Existing packages not modified.

## Error handling + correctness rules (mandatory)

- Empty `tool_calls` from LLM must raise `APIError`, not return empty results silently.
- Malformed LLM output (validation error during parsing) must raise `APIError` (FR-11).
- Mixed-language input must raise `ValueError` immediately, not attempt partial extraction.
- Unsupported POS must be logged at WARNING level with the word form and POS value.

## Zero legacy tolerance rule (mandatory)

- No fallback parsing for malformed LLM responses.
- No generic/untyped payloads — every result goes through the POS-specific Pydantic model.

## Acceptance criteria (testable)

1. `WordDetailsExtractor("nl", "ru")` succeeds; `WordDetailsExtractor("en", "ru")` raises `ValueError`.
2. `extract([])` returns `[]` without any external calls.
3. `extract([Word(language=NL, ...), Word(language=RU, ...)])` raises `ValueError` (mixed languages).
4. `extract([Word(word_type=NOUN, ...), Word(word_type=VERB, ...)])` dispatches to separate POS-specific chains and merges results in input order.
5. Unsupported POS words are skipped with WARNING log and omitted from results.
6. Malformed LLM output raises `APIError`.
7. Integration test: live extraction of a Dutch noun returns a valid `DetailedWordRecord` with `schema_key="nl_ru_noun"`, `schema_version=1`, and a `payload` that validates against `NlRuNounDetails`.
8. `make check` passes in `packages/extract_word_details/`.

## Verification / quality gates

- [x] Unit tests added (service, dispatch, error paths)
- [x] Integration tests added (live extraction per POS)
- [x] E2E tests added (mixed-POS batch extraction)
- [x] Linters/formatters pass
- [x] No new warnings introduced
- [x] Negative-path tests (invalid pair, mixed lang, empty tool_calls, malformed output)
- [x] No file exceeds 200 lines

## Edge cases

- Single-word batch: should work the same as multi-word
- All words are unsupported POS: result is `[]`, no LLM call
- Batch with duplicate words (same normalized_form, same POS): each gets its own result
- LLM returns fewer results than input for a POS group: validation must catch this and raise `APIError`

## Notes / risks

- **Dependency resolution**: `extract_word_details` depends on `database` for `DetailedWordRecord`. This is a one-way dependency (no circular). The `database` module references the extractor only through a Protocol (duck typing, injected).
- **API latency**: Integration tests may be slow (up to 60s for 10 words). The spec allows this (NFR-2).
- **Prompt quality**: The LLM output quality depends on prompt design (T2). If integration tests fail due to LLM output, the issue is likely in the prompt — fix in T2's prompt scripts, not by adding fallback parsing.
