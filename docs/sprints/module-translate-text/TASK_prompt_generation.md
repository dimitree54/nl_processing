---
Task ID: `T1`
Title: `Create Dutch-to-Russian translation prompt with few-shot examples`
Sprint: `2026-03-03_translate-text`
Module: `translate_text`
Depends on: `--`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

A working Dutch-to-Russian translation prompt JSON file (`nl_ru.json`) exists in the module's `prompts/` directory, with carefully curated few-shot translation examples that demonstrate natural Russian output and markdown preservation. The prompt is the core intellectual asset of this module.

## Context (contract mapping)

- Requirements: `nl_processing/translate_text/docs/prd_translate_text.md` -- FR9 (few-shot examples), FR2 (markdown preservation), FR3 (natural Russian), FR4 (clean output), FR10 (close to original)
- Architecture: `nl_processing/translate_text/docs/architecture_translate_text.md` -- "Prompt-as-Product", "Markdown Preservation via Prompt Engineering", "Prompt File Naming"
- Reference: `nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`

## Preconditions

- `nl_processing/core/prompts.py` exists and `load_prompt()` works
- LangChain and langchain-openai are installed

## Non-goals

- Prompt optimization or extensive tuning (iterate based on T4 test results)
- Service class implementation (that's T2)
- Quality testing (that's T4)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/translate_text/prompts/generate_nl_ru_prompt.py` -- create
- `nl_processing/translate_text/prompts/nl_ru.json` -- create (generated artifact)

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/extract_text_from_image/`, `nl_processing/extract_words_from_text/`, `nl_processing/translate_word/`
- Any test files, `service.py`

**Test scope:**
- No tests in this task. Verify by running the generation script.
- Verification: `uv run python nl_processing/translate_text/prompts/generate_nl_ru_prompt.py`

## Touched surface (expected files / modules)

- `nl_processing/translate_text/prompts/generate_nl_ru_prompt.py` -- new
- `nl_processing/translate_text/prompts/nl_ru.json` -- new (generated)

## Dependencies and sequencing notes

- No dependencies. This is the first task.
- T2 depends on this producing a valid `nl_ru.json`.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-core` (>=0.3)
  - **Prompt template**: `ChatPromptTemplate.from_messages()` with `SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`, `MessagesPlaceholder`
  - **Serialization**: `langchain_core.load.dumpd()` to produce JSON-serializable dict
  - **Tool calls in few-shot examples**: `AIMessage(content="", tool_calls=[{"name": "...", "args": {...}, "id": "..."}])`
  - **Pattern** (from reference): Build prompt, `dumpd()`, `json.dump()` to file

## Implementation steps (developer-facing)

1. **Create directory** `nl_processing/translate_text/prompts/` (if not exists).

2. **Create `generate_nl_ru_prompt.py`** with:

   a. **System instruction** (in Russian, as the target language):
      - You are a professional translator from Dutch to Russian
      - Translate the provided text naturally, keeping the meaning close to the original
      - Preserve all markdown formatting (headings, bold, italic, lists, paragraph breaks)
      - Return only the translated text -- no comments, explanations, or prefixes
      - If the input is empty or contains no Dutch text, return an empty string

   b. **Internal wrapper Pydantic model** for structured output:
      ```python
      class _TranslatedText(BaseModel):
          text: str
      ```
      This ensures clean output (no LLM chatter) via tool calling.

   c. **Few-shot examples** (3-5 pairs), each as `HumanMessage` + `AIMessage` (with `tool_calls`) + `ToolMessage` triplets:

      - **Example 1** (simple sentence):
        - Input: `"De zon schijnt vandaag."`
        - Output: `"Сегодня светит солнце."`

      - **Example 2** (markdown with headings and bold):
        - Input: `"# Welkom\n\nDit is een **belangrijk** bericht."`
        - Output: `"# Добро пожаловать\n\nЭто **важное** сообщение."`

      - **Example 3** (list + italic):
        - Input: `"Wat heb je nodig:\n\n- *Melk*\n- *Brood*\n- *Kaas*"`
        - Output: `"Что тебе нужно:\n\n- *Молоко*\n- *Хлеб*\n- *Сыр*"`

      - **Example 4** (empty input):
        - Input: `""`
        - Output: `""`

      - **Example 5** (non-Dutch text):
        - Input: `"The quick brown fox jumps over the lazy dog."`
        - Output: `""`

   d. **`MessagesPlaceholder(variable_name="text")`** as the final placeholder.

   e. **Serialize** with `dumpd()` and save to `nl_ru.json`.

3. **Run the generation script**: `uv run python nl_processing/translate_text/prompts/generate_nl_ru_prompt.py`

4. **Verify** the JSON loads: `load_prompt("nl_processing/translate_text/prompts/nl_ru.json")`

5. **File must be under 200 lines** (pylint limit).

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: N/A -- static file generation only.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the exact prompt generation pattern from `extract_text_from_image`.
- **Correct libraries only**: `langchain-core` (>=0.3).
- **Correct file locations**: `nl_processing/translate_text/prompts/`.

## Error handling + correctness rules (mandatory)

- Generation script should fail clearly if any step fails.
- Few-shot translations must be linguistically accurate Russian.

## Zero legacy tolerance rule (mandatory)

- No legacy files to remove (new files only).

## Acceptance criteria (testable)

1. `generate_nl_ru_prompt.py` exists and is executable
2. `nl_ru.json` exists after running the script
3. `load_prompt("nl_processing/translate_text/prompts/nl_ru.json")` succeeds
4. Prompt contains system instruction, >= 3 few-shot examples, and a `MessagesPlaceholder`
5. Few-shot examples demonstrate: markdown preservation, empty-string handling, natural Russian
6. Generation script is under 200 lines
7. Ruff format and check pass

## Verification / quality gates

- [ ] Generation script runs without error
- [ ] `nl_ru.json` loadable by `core.prompts.load_prompt()`
- [ ] Ruff passes
- [ ] Pylint 200-line limit passes
- [ ] Few-shot Russian translations are linguistically correct

## Edge cases

- The `_TranslatedText` wrapper model name must match between the generation script and T2's service implementation
- Empty string and non-Dutch examples are critical for T2's edge-case handling

## Notes / risks

- **Risk**: Few-shot examples may not be sufficient for high-quality translations.
  - **Mitigation**: Start with clear, diverse examples. Iterate based on T4 integration test results.
- **Decision made autonomously**: Using Russian for the system instruction (target language convention) to align with the module's language extensibility pattern.
