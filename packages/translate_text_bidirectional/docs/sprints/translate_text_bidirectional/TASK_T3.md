---
Task ID: `T3`
Title: `Create bidirectional prompt asset with direction-specific tool examples`
Sprint: `2026-03-12_translate-text-bidirectional`
Module: `translate_text_bidirectional`
Depends on: `T2`
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Create the combined bidirectional prompt asset that teaches the model to: (1) identify whether input is Dutch or Russian, (2) call the appropriate direction-specific tool, and (3) handle edge cases (empty input, non-NL/RU text). The prompt generator script and the generated JSON are the source of truth for translation behavior.

## Context (contract mapping)

- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md` — DEC-2 (one combined prompt), DEC-3 (two direction-specific tools, model chooses), IF-3, CR-3, CR-5
- Reference: `packages/translate_text/src/nl_processing/translate_text/prompts/generate_nl_ru_prompt.py` — existing prompt pattern
- Reference: `packages/translate_text/src/nl_processing/translate_text/prompts/nl_ru.json` — generated prompt format

## Preconditions

- T2 completed (package scaffolding and `prompts/` directory exist).
- Two tool schema names must be decided here for use in the prompt and later in the service (T4).

## Non-goals

- Writing the service that loads and uses this prompt (T4).
- Writing tests for prompt behavior (T4–T6 verify through the service).
- Supporting language pairs beyond NL <-> RU.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/prompts/` — create prompt generator and generated JSON

**FORBIDDEN — this task must NEVER touch:**
- `packages/translate_text/` — reference only
- `packages/core/` — already extended in T1
- Any other package

**Test scope:**
- No tests in this task — prompt correctness is verified through service tests in T4–T6.
- Run `make check` to verify ruff/pylint pass on the new prompt script.

## Touched surface (expected files / modules)

- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/prompts/__init__.py` (empty)
- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/prompts/generate_nl_ru_bidirectional_prompt.py`
- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/prompts/nl_ru_bidirectional.json` (generated artifact)

## Dependencies and sequencing notes

- Depends on T2 for directory structure.
- T4 will import tool schema names from this prompt to define `Pydantic` models that match.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-core` (already in repo, `>=0.3,<1`)
  - **Documentation**: https://python.langchain.com/docs/concepts/prompt_templates/
  - **API reference**: `ChatPromptTemplate.from_messages()`, `MessagesPlaceholder`
  - **Usage**: System message + few-shot triplets (Human → AI with tool_calls → ToolMessage) + MessagesPlaceholder
  - **Serialization**: `langchain_core.load.dumpd()` produces JSON; `langchain_core.load.load()` reconstructs.
- **Library**: `nl_processing.core.scripts.prompt_author` (internal)
  - **Usage**: `save_prompt(prompt, path)` — serializes and writes to disk.

## Implementation steps (developer-facing)

1. **Define two tool names** that will be used in the prompt and matched by Pydantic models in the service:
   - `_NlToRuTranslation` — called when input is Dutch, outputs Russian text.
   - `_RuToNlTranslation` — called when input is Russian, outputs Dutch text.

2. **Create `prompts/__init__.py`** — empty file.

3. **Create `prompts/generate_nl_ru_bidirectional_prompt.py`** following the pattern in `translate_text/prompts/generate_nl_ru_prompt.py`:

   a. **System instruction** (in Russian for consistency with existing prompts):
      - "You are a professional bidirectional translator between Dutch and Russian."
      - "Determine the dominant language of the input (Dutch or Russian)."
      - "If Dutch, translate to Russian using the `_NlToRuTranslation` tool."
      - "If Russian, translate to Dutch using the `_RuToNlTranslation` tool."
      - "Preserve all markdown formatting."
      - "Return only the translated text — no comments, explanations, or prefixes."
      - "If input is empty or contains neither Dutch nor Russian, call either tool with an empty string."

   b. **Few-shot examples** — triplets of (HumanMessage, AIMessage with tool_call, ToolMessage):
      - **Example 1**: NL→RU simple sentence: "De zon schijnt vandaag." → tool `_NlToRuTranslation` → "Сегодня светит солнце."
      - **Example 2**: RU→NL simple sentence: "Сегодня светит солнце." → tool `_RuToNlTranslation` → "De zon schijnt vandaag."
      - **Example 3**: NL→RU markdown: "# Welkom\n\nDit is een **belangrijk** bericht." → tool `_NlToRuTranslation` → "# Добро пожаловать\n\nЭто **важное** сообщение."
      - **Example 4**: RU→NL markdown: "# Добро пожаловать\n\nЭто **важное** сообщение." → tool `_RuToNlTranslation` → "# Welkom\n\nDit is een **belangrijk** bericht."
      - **Example 5**: NL→RU list: "Wat heb je nodig:\n\n- *Melk*\n- *Brood*\n- *Kaas*" → tool `_NlToRuTranslation` → "Что тебе нужно:\n\n- *Молоко*\n- *Хлеб*\n- *Сыр*"
      - **Example 6**: RU→NL list: "Что тебе нужно:\n\n- *Молоко*\n- *Хлеб*\n- *Сыр*" → tool `_RuToNlTranslation` → "Wat heb je nodig:\n\n- *Melk*\n- *Brood*\n- *Kaas*"
      - **Example 7**: Empty input → tool `_NlToRuTranslation` → "" (either tool is acceptable)
      - **Example 8**: Non-NL/RU English text: "The quick brown fox." → tool `_NlToRuTranslation` → "" (unsupported language returns empty)

   c. **End with** `MessagesPlaceholder(variable_name="text")`.

   d. **`build_prompt()` function** that constructs and returns the `ChatPromptTemplate`.

   e. **`if __name__ == "__main__"`** block that calls `save_prompt(build_prompt(), str(OUTPUT_PATH))`.

4. **Generate the prompt JSON**: Run the generator script:
   ```bash
   cd packages/translate_text_bidirectional
   uv run python src/nl_processing/translate_text_bidirectional/prompts/generate_nl_ru_bidirectional_prompt.py
   ```

5. **Verify** the generated JSON file exists at `prompts/nl_ru_bidirectional.json` and is valid.

6. **Run `make check`** from `packages/translate_text_bidirectional/` to verify ruff/pylint pass on the prompt script. Ensure the script stays under 200 lines.

## Production safety constraints (mandatory)

- No database operations.
- No API calls during prompt generation (pure template construction).
- No shared resources affected.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses `core.scripts.prompt_author.save_prompt` for serialization.
- **Correct libraries only**: `langchain-core` message types and prompt templates.
- **Correct file locations**: Prompt files live in `src/nl_processing/translate_text_bidirectional/prompts/`.

## Error handling + correctness rules (mandatory)

- Generator script must fail loudly if serialization fails — no silent empty files.
- `save_prompt` already prints summary; no additional error handling needed.

## Zero legacy tolerance rule (mandatory)

- No legacy exists — fresh prompt asset.

## Acceptance criteria (testable)

1. `generate_nl_ru_bidirectional_prompt.py` exists and is runnable.
2. `nl_ru_bidirectional.json` is generated and contains a valid LangChain `ChatPromptTemplate` serialization.
3. Prompt includes system instruction teaching bidirectional direction selection.
4. Prompt includes at least 4 NL→RU examples and at least 2 RU→NL examples as few-shot triplets.
5. Each example uses the correct direction-specific tool name.
6. Edge cases (empty input, non-NL/RU) are covered in examples.
7. `make check` passes from package directory (ruff, pylint on prompt script).
8. All files stay under 200 lines.

## Verification / quality gates

- [ ] `nl_ru_bidirectional.json` file exists and is valid JSON
- [ ] Prompt can be loaded: `load_prompt(path)` returns a `ChatPromptTemplate`
- [ ] `make check` passes (ruff/pylint on the prompt generator script)
- [ ] Generator script under 200 lines
- [ ] `build_prompt()` is importable for testing

## Edge cases

- Ensure tool names in few-shot examples match exactly the Pydantic class names that will be defined in T4: `_NlToRuTranslation` and `_RuToNlTranslation`.
- Ensure the `MessagesPlaceholder` variable name is `"text"` to match the service's invoke call pattern.

## Notes / risks

- **Risk**: Prompt quality for direction inference depends on few-shot example balance between NL→RU and RU→NL.
  - **Mitigation**: Include examples of both directions, plus edge cases. Integration tests in T5 will validate.
- **Risk**: Generator script approaching 200 lines due to many examples.
  - **Mitigation**: Keep example text inline as constants. If needed, factor helper functions. Monitor line count.
