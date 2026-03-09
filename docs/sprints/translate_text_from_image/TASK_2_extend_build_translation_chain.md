---
Task ID: T2
Title: Extend `build_translation_chain()` with optional LLM kwargs
Sprint: `translate_text_from_image`
Module: `core`
Depends on: --
Parallelizable: yes, with T1
Owner: Developer
Status: planned
---

## Goal / value

Extend `build_translation_chain()` in `core/prompts.py` to accept optional `reasoning_effort`, `service_tier`, and `temperature` parameters, passing them to `ChatOpenAI`. This enables the new `translate_text_from_image` module (and future callers) to configure LLM behavior while maintaining full backward compatibility with existing callers like `translate_text`.

## Context (contract mapping)

- Module spec: `packages/translate_text_from_image/docs/module-spec.md` — FR-1, DEC-2, IF-3
- Current code: `packages/core/src/nl_processing/core/prompts.py` — `build_translation_chain()` hardcodes `temperature=0`
- Pattern: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/service.py` — already passes these kwargs directly to `ChatOpenAI`

## Preconditions

- `packages/core/` exists and is a working package.
- `packages/translate_text/` tests pass before this change (existing caller of `build_translation_chain`).

## Non-goals

- Modifying `translate_text` to use the new kwargs (it can adopt them later).
- Adding other `ChatOpenAI` parameters beyond the three specified.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/core/src/nl_processing/core/prompts.py` — extend function signature

**FORBIDDEN — this task must NEVER touch:**
- `packages/translate_text/` — existing caller should work unchanged
- `packages/extract_text_from_image/` — handled in T1
- Any test files

**Test scope:**
- Verify backward compatibility: `make -C packages/translate_text check`
- The function signature change is additive (optional kwargs) so existing callers continue working.

## Touched surface (expected files / modules)

- `packages/core/src/nl_processing/core/prompts.py`

## Dependencies and sequencing notes

- No dependencies. Can run in parallel with T1.
- T3 depends on this task (new service will call `build_translation_chain` with the new kwargs).

## Implementation steps

1. **Open `packages/core/src/nl_processing/core/prompts.py`** and modify `build_translation_chain()`:

   Add three optional keyword arguments to the function signature:
   ```python
   def build_translation_chain(
       *,
       source_language: Language,
       target_language: Language,
       supported_pairs: set[tuple[str, str]],
       prompts_dir: pathlib.Path,
       tool_schema: type[BaseModel],
       model: str,
       reasoning_effort: str | None = None,
       service_tier: str | None = None,
       temperature: float | None = 0,
   ) -> RunnableSerializable:
   ```

2. **Update the `ChatOpenAI` construction** inside the function body:
   Replace:
   ```python
   llm = ChatOpenAI(model=model, temperature=0).bind_tools(...)
   ```
   With:
   ```python
   llm = ChatOpenAI(
       model=model,
       temperature=temperature,
       reasoning_effort=reasoning_effort,
       service_tier=service_tier,
   ).bind_tools(...)
   ```

3. **Update the docstring** to document the three new parameters:
   - `reasoning_effort`: Optional reasoning effort level for the model.
   - `service_tier`: Optional service tier for the OpenAI API.
   - `temperature`: LLM temperature (default 0 for deterministic output).

4. **Verify backward compatibility**: Run `make -C packages/translate_text check`. The existing `TextTranslator` calls `build_translation_chain()` without these kwargs, so it should receive the defaults (`reasoning_effort=None`, `service_tier=None`, `temperature=0`) — exactly matching the previous hardcoded behavior.

5. **Verify file size**: `prompts.py` should stay well under 200 lines (currently 98, adding ~6 lines).

## Production safety constraints

- No database operations.
- No shared resource changes.
- Purely additive API change with default values matching previous behavior.

## Anti-disaster constraints

- **Reuse before build**: Extending existing shared infrastructure, not duplicating.
- **No regressions**: Default values match previous hardcoded `temperature=0`. Existing callers are unaffected.
- **Correct libraries only**: `ChatOpenAI` already accepts `reasoning_effort`, `service_tier`, `temperature` — this was verified from the `extract_text_from_image` service which already passes them.

## Error handling + correctness rules

- No new error handling needed. The parameters are passed directly to `ChatOpenAI` which handles validation.
- Do not wrap or swallow any errors.

## Zero legacy tolerance rule

- The hardcoded `temperature=0` is replaced with a parameterized `temperature` with default `0`. No dead code.

## Acceptance criteria (testable)

1. `build_translation_chain()` accepts `reasoning_effort`, `service_tier`, `temperature` as optional keyword arguments.
2. Default values: `reasoning_effort=None`, `service_tier=None`, `temperature=0`.
3. `make -C packages/translate_text check` passes (backward compatibility).
4. `prompts.py` is under 200 lines.
5. Docstring updated to document the new parameters.

## Verification / quality gates

- [x] Linters/formatters pass
- [x] No new warnings introduced
- [x] Backward compatibility verified via `make -C packages/translate_text check`

## Edge cases

- `temperature=None` is valid for `ChatOpenAI` (uses the API default). This is different from `temperature=0` but the default preserves existing behavior.
- `reasoning_effort` and `service_tier` with `None` are handled correctly by `ChatOpenAI` (ignored).

## Notes / risks

- **Risk**: The `ChatOpenAI` constructor might not accept `reasoning_effort` or `service_tier` in the installed version.
  - **Mitigation**: The `extract_text_from_image` service already uses these exact parameters successfully (see `service.py` line 42-43), confirming the installed `langchain-openai` version supports them.
