---
Task ID: `T1`
Title: `Extend core with multi-tool bidirectional chain builder`
Sprint: `2026-03-12_translate-text-bidirectional`
Module: `translate_text_bidirectional` (touches `core` for shared infra)
Depends on: —
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Add a `build_bidirectional_translation_chain` function to `core/prompts.py` that accepts multiple tool schemas and uses model-decided tool choice (no forced tool). This enables the bidirectional translator to present two direction-specific tools to the model and let it choose which to call based on input language.

## Context (contract mapping)

- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md` — DEC-3, DEC-4, IF-2, CR-4
- Core prompts: `packages/core/src/nl_processing/core/prompts.py` — existing `build_translation_chain`
- Reference: `packages/translate_text/src/nl_processing/translate_text/service.py` — current single-tool usage

## Preconditions

- Core package exists and `build_translation_chain` works for one-way callers.

## Non-goals

- Modifying the existing `build_translation_chain` signature or behavior.
- Writing the bidirectional service or prompt asset (later tasks).
- Writing tests for the bidirectional package (later tasks).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/core/src/nl_processing/core/prompts.py` — add new function
- `packages/translate_text/tests/` — run existing tests to verify no regression

**FORBIDDEN — this task must NEVER touch:**
- `packages/translate_text/src/` — no changes to sibling package source
- Any other package's code or tests
- The existing `build_translation_chain` function signature

**Test scope:**
- Verify existing `translate_text` package tests still pass: `make check` from `packages/translate_text/`
- No new test files created in this task (unit tests for the new function will be exercised via T4)

## Touched surface (expected files / modules)

- `packages/core/src/nl_processing/core/prompts.py` — add `build_bidirectional_translation_chain`

## Dependencies and sequencing notes

- No prior task dependencies.
- T2–T7 all depend on this function existing.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-openai` (already in repo, `>=0.3,<1`)
  - **Documentation**: https://python.langchain.com/docs/integrations/chat/openai/
  - **API reference**: `ChatOpenAI.bind_tools(tools, tool_choice=...)` — when `tool_choice` is omitted or set to `"auto"`, the model decides which tool to call.
  - **Usage**: `llm.bind_tools([ToolA, ToolB])` — no `tool_choice` parameter means model auto-selects.
  - **Known gotchas**: When `tool_choice` is set to a specific tool name, the model is forced. Omitting it or passing `"auto"` lets the model choose. With multiple tools and `"auto"`, the model may call zero tools — the caller must handle that.
- **Library**: `langchain-core` (already in repo, `>=0.3,<1`)
  - **Documentation**: https://python.langchain.com/docs/concepts/runnables/
  - **API reference**: `RunnableSerializable` chain composition via `prompt | llm`.

## Implementation steps (developer-facing)

1. Open `packages/core/src/nl_processing/core/prompts.py`.
2. Add a new function `build_bidirectional_translation_chain` below the existing `build_translation_chain`. The function signature:
   ```python
   def build_bidirectional_translation_chain(
       *,
       language_a: Language,
       language_b: Language,
       supported_pairs: set[frozenset[str]],
       prompts_dir: pathlib.Path,
       prompt_file: str,
       tool_schemas: list[type[BaseModel]],
       model: str,
       service_tier: str | None = None,
       temperature: float | None = 0,
   ) -> RunnableSerializable:
   ```
3. Validate that `frozenset({language_a.value, language_b.value})` is in `supported_pairs`. Raise `ValueError` if not.
4. Load the prompt using existing `load_prompt(str(prompts_dir / prompt_file))`.
5. Create a `ChatOpenAI` instance with `model`, `temperature`, `service_tier`.
6. Call `.bind_tools(tool_schemas)` — **without** `tool_choice` parameter, which defaults to `"auto"` (model decides).
7. Return `prompt | llm`.
8. Run `make check` from `packages/translate_text/` to verify no regression to the existing one-way chain builder.
9. Verify `packages/core/src/nl_processing/core/prompts.py` stays under 200 lines. If it would exceed, extract helper functions or split into a second file (e.g., `core/chain_builders.py`).

## Production safety constraints (mandatory)

- No database operations.
- No ports, sockets, or shared resources.
- The function is purely additive — existing callers are unaffected.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses `ChatOpenAI`, `load_prompt`, and chain composition patterns from the existing function.
- **Correct libraries only**: `langchain-openai>=0.3,<1` and `langchain-core>=0.3,<1` (from root `pyproject.toml`).
- **No regressions**: Existing `build_translation_chain` is unchanged; `translate_text` tests must remain green.

## Error handling + correctness rules (mandatory)

- `ValueError` for unsupported pairs — fail fast, no fallback.
- `FileNotFoundError` / `ValueError` / `TypeError` from `load_prompt` propagate unchanged.
- No empty catch blocks. No default returns.

## Zero legacy tolerance rule (mandatory)

- No old code is being replaced. This is purely additive.
- Avoid duplicating logic from `build_translation_chain` — share helpers if beneficial.

## Acceptance criteria (testable)

1. `build_bidirectional_translation_chain` exists in `core/prompts.py` and is importable.
2. It accepts `frozenset`-based pair validation for unordered language pairs.
3. It binds multiple tool schemas without forcing a specific tool choice.
4. It returns a `RunnableSerializable` (prompt | llm chain).
5. Existing `translate_text` package `make check` passes without modification.
6. `core/prompts.py` stays under 200 lines.

## Verification / quality gates

- [ ] New function is importable: `from nl_processing.core.prompts import build_bidirectional_translation_chain`
- [ ] Existing tests pass: `make check` from `packages/translate_text/`
- [ ] No new warnings introduced in `ruff check` or `pylint`
- [ ] File size under 200 lines

## Edge cases

- Passing the same language for both `language_a` and `language_b` should raise `ValueError` (pair won't be in supported set).
- Empty `tool_schemas` list — not a design concern; caller is expected to pass exactly 2 schemas.

## Notes / risks

- **Risk**: File size — `prompts.py` is currently 109 lines. Adding ~40 lines for the new function should stay under 200.
  - **Mitigation**: Monitor line count. If close, extract shared validation logic.
- **Risk**: `tool_choice="auto"` vs omitting `tool_choice` — behavior must be verified.
  - **Mitigation**: LangChain defaults to `"auto"` when `tool_choice` is not passed. Simply omit the parameter.
