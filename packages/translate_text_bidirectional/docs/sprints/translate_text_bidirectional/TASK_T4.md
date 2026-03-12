---
Task ID: `T4`
Title: `Implement BidirectionalTextTranslator service with unit tests`
Sprint: `2026-03-12_translate-text-bidirectional`
Module: `translate_text_bidirectional`
Depends on: `T3`
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Implement the `BidirectionalTextTranslator` service class with the full `translate(text) -> str` API. Include comprehensive unit tests covering constructor behavior, blank input short-circuit, tool result parsing for both directions, and error wrapping. After this task, the service is functional and unit-tested.

## Context (contract mapping)

- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md` — FR-1 through FR-11, BR-1 through BR-7, DEC-1, DEC-3
- Core chain builder: T1's `build_bidirectional_translation_chain` from `core/prompts.py`
- Prompt asset: T3's `nl_ru_bidirectional.json`
- Reference: `packages/translate_text/src/nl_processing/translate_text/service.py`

## Preconditions

- T1 completed (`build_bidirectional_translation_chain` available in `core/prompts.py`).
- T2 completed (package scaffolding, test directories, conftest.py exist).
- T3 completed (prompt asset generated at `prompts/nl_ru_bidirectional.json`).

## Non-goals

- Live API testing (T5).
- E2E quality testing (T6).
- Monorepo integration (T7).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/service.py` — implement service
- `packages/translate_text_bidirectional/tests/conftest.py` — adapt shared test helpers for bidirectional tool responses
- `packages/translate_text_bidirectional/tests/unit/translate_text_bidirectional/` — unit test files
- `packages/translate_text_bidirectional/tests/unit/translate_text_bidirectional/conftest.py` — unit-level fixtures

**FORBIDDEN — this task must NEVER touch:**
- `packages/translate_text/` — reference only
- `packages/core/` — already extended in T1
- Any other package

**Test scope:**
- Tests go in: `packages/translate_text_bidirectional/tests/unit/translate_text_bidirectional/`
- Test command: `make check` from `packages/translate_text_bidirectional/`

## Touched surface (expected files / modules)

- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/service.py`
- `packages/translate_text_bidirectional/tests/conftest.py`
- `packages/translate_text_bidirectional/tests/unit/translate_text_bidirectional/conftest.py`
- `packages/translate_text_bidirectional/tests/unit/translate_text_bidirectional/test_bidirectional_translator.py`
- `packages/translate_text_bidirectional/tests/unit/translate_text_bidirectional/test_error_handling.py`

## Dependencies and sequencing notes

- Depends on T1 (core function), T2 (scaffold), T3 (prompt asset).
- T5 and T6 depend on this service implementation.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-core` (`>=0.3,<1`)
  - **API**: `HumanMessage`, `AIMessage.tool_calls` — list of dicts with `"name"`, `"args"`, `"id"` keys.
  - **Documentation**: https://python.langchain.com/docs/concepts/messages/
  - **Key detail**: When model chooses a tool, `response.tool_calls[0]["name"]` contains the tool class name, and `response.tool_calls[0]["args"]` contains the parsed arguments dict.
- **Library**: `pydantic` (`>=2.0,<3`)
  - **Usage**: Tool schema classes as `BaseModel` subclasses. The class `__name__` becomes the tool name in the API.
- **Library**: `nl_processing.core.prompts.build_bidirectional_translation_chain` (from T1)
  - **Usage**: Called in constructor with pair, prompt dir, tool schemas, model config.
- **Library**: `nl_processing.core.exceptions.APIError` (from core)
  - **Usage**: Wrap all runtime errors from chain invocation.

## Implementation steps (developer-facing)

### Service implementation (`service.py`)

1. **Define two Pydantic tool schemas** matching prompt tool names:
   ```python
   class _NlToRuTranslation(BaseModel):
       text: str

   class _RuToNlTranslation(BaseModel):
       text: str
   ```

2. **Define supported pair** as a `frozenset`-based set:
   ```python
   _SUPPORTED_PAIRS: set[frozenset[str]] = {frozenset({"nl", "ru"})}
   ```

3. **Define prompts directory and prompt file name**:
   ```python
   _PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"
   _PROMPT_FILE = "nl_ru_bidirectional.json"
   ```

4. **Implement `BidirectionalTextTranslator`**:
   ```python
   class BidirectionalTextTranslator:
       def __init__(
           self,
           *,
           source_language: Language,
           target_language: Language,
           model: str = "gpt-4.1-mini",
           service_tier: str | None = "priority",
       ) -> None:
           self._source_language = source_language
           self._target_language = target_language
           self._chain = build_bidirectional_translation_chain(
               language_a=source_language,
               language_b=target_language,
               supported_pairs=_SUPPORTED_PAIRS,
               prompts_dir=_PROMPTS_DIR,
               prompt_file=_PROMPT_FILE,
               tool_schemas=[_NlToRuTranslation, _RuToNlTranslation],
               model=model,
               service_tier=service_tier,
           )
   ```
   Note: Constructor parameter names are `source_language`/`target_language` for API continuity (DEC-1), but the pair is validated as unordered (CR-1).

5. **Implement `translate` method**:
   ```python
   async def translate(self, text: str) -> str:
       if not text.strip():
           return ""
       try:
           response = await self._chain.ainvoke({"text": [HumanMessage(content=text)]})
           tool_call = response.tool_calls[0]
           # Accept either direction tool's result
           result_text = tool_call["args"]["text"]
       except Exception as e:
           raise APIError(str(e)) from e
       return result_text
   ```
   The service does not need to check which tool was called — both tools return `{"text": str}`. It simply extracts the text.

6. **Verify `service.py`** stays under 200 lines.

### Test implementation

7. **Update `tests/conftest.py`** to support bidirectional tool responses:
   - Keep `AsyncChainMock`, `AsyncChainMockError`, `make_tool_response` (from T2).
   - `make_tool_response` should accept `args: dict[str, object]` and optionally a tool name:
     ```python
     def make_tool_response(args: dict[str, object], tool_name: str = "_NlToRuTranslation") -> SimpleNamespace:
         resp = SimpleNamespace()
         resp.tool_calls = [{"name": tool_name, "args": args}]
         return resp
     ```

8. **Update `tests/unit/translate_text_bidirectional/conftest.py`** to re-export and add helpers:
   ```python
   from tests.conftest import (
       AsyncChainMock as _AsyncChainMock,
       AsyncChainMockError as _AsyncChainMockError,
       make_tool_response as _make_response,
   )

   def make_nl_to_ru_response(text: str) -> object:
       return _make_response({"text": text}, "_NlToRuTranslation")

   def make_ru_to_nl_response(text: str) -> object:
       return _make_response({"text": text}, "_RuToNlTranslation")
   ```

9. **Create `test_bidirectional_translator.py`** with tests mirroring `translate_text` unit tests:
   - `test_constructor_valid_pair_nl_ru` — NL, RU order
   - `test_constructor_valid_pair_ru_nl` — RU, NL order (both must succeed per CR-1)
   - `test_constructor_unsupported_pair` — e.g., NL, NL → ValueError
   - `test_constructor_custom_model` — custom model/service_tier
   - `test_constructor_uses_priority_tier_by_default` — verify default `service_tier="priority"`
   - `test_translate_nl_to_ru_happy_path` — mock chain returns `_NlToRuTranslation` tool result
   - `test_translate_ru_to_nl_happy_path` — mock chain returns `_RuToNlTranslation` tool result
   - `test_translate_empty_input` — returns "" without chain call
   - `test_translate_whitespace_input` — returns "" without chain call
   - `test_translate_invokes_chain` — verify chain.ainvoke called with correct structure

10. **Create `test_error_handling.py`** mirroring `translate_text` error tests:
    - `test_api_error_wrapping` — RuntimeError → APIError
    - `test_api_error_various_exceptions` — multiple exception types
    - `test_api_error_preserves_cause` — `__cause__` chain preserved

11. **Run `make check`** and ensure all unit tests pass, ruff/pylint green.

12. **Verify** all test files and service file stay under 200 lines. Split if needed.

## Production safety constraints (mandatory)

- No database operations.
- No live API calls (unit tests use mocks).
- No shared resources affected.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses `build_bidirectional_translation_chain` from core. Mirrors `translate_text` service pattern.
- **Correct libraries only**: All dependencies declared in T2's `pyproject.toml`.
- **No regressions**: This task only adds new files; no existing code modified.

## Error handling + correctness rules (mandatory)

- All exceptions from chain invocation wrapped as `APIError` with cause preserved.
- No empty catch blocks.
- No default returns on failure — fail fast.
- Blank input short-circuits to `""` without chain invocation (FR-7, BR-4).

## Zero legacy tolerance rule (mandatory)

- No legacy exists — fresh implementation.

## Acceptance criteria (testable)

1. `BidirectionalTextTranslator` is importable from `nl_processing.translate_text_bidirectional.service`.
2. Constructor accepts `(source_language=Language.NL, target_language=Language.RU)` — succeeds.
3. Constructor accepts `(source_language=Language.RU, target_language=Language.NL)` — succeeds (CR-1).
4. Constructor rejects unsupported pairs with `ValueError`.
5. `translate("")` returns `""` without invoking the chain.
6. `translate("   \n  ")` returns `""` without invoking the chain.
7. `translate(dutch_text)` with mocked NL→RU tool response returns the expected Russian text.
8. `translate(russian_text)` with mocked RU→NL tool response returns the expected Dutch text.
9. Chain exceptions are wrapped as `APIError` with original cause preserved.
10. `make check` passes (all unit tests, ruff, pylint).
11. All files under 200 lines.

## Verification / quality gates

- [ ] Unit tests pass: `make check` from `packages/translate_text_bidirectional/`
- [ ] All constructor variants tested (both orders, unsupported, custom model)
- [ ] Both direction tool responses tested
- [ ] Error wrapping tested with cause preservation
- [ ] Blank input short-circuit tested with chain non-invocation assertion
- [ ] Linters/formatters pass
- [ ] No new warnings
- [ ] Files under 200 lines

## Edge cases

- Constructor with same language twice (e.g., NL, NL) — must raise `ValueError`.
- Response with empty `tool_calls` list — should raise `APIError` (IndexError caught and wrapped).
- Response with missing `"args"` key — should raise `APIError` (KeyError caught and wrapped).

## Notes / risks

- **Risk**: Tool parsing assumes `response.tool_calls[0]` exists and has `"args"` with `"text"`. If the model returns no tool call, this raises `IndexError` → wrapped as `APIError`. This is correct behavior per FR-10 / FM-5.
- **Risk**: `service.py` line count — estimated ~65 lines (matching `translate_text/service.py`). Well under 200.
