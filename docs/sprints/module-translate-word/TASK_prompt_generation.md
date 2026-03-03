---
Task ID: `T1`
Title: `Create Dutch-to-Russian word translation prompt with few-shot examples`
Sprint: `2026-03-03_translate-word`
Module: `translate_word`
Depends on: `--`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

A working Dutch-to-Russian word translation prompt JSON file (`nl_ru.json`) exists in the module's `prompts/` directory, with few-shot examples demonstrating batch word translation with one-to-one order-preserving mapping.

## Context (contract mapping)

- Requirements: `nl_processing/translate_word/docs/prd_translate_word.md` -- FR7 (few-shot prompt JSONs), FR3 (one-to-one mapping)
- Architecture: `nl_processing/translate_word/docs/architecture_translate_word.md` -- "Single LLM Call Per Batch", "One-to-One Order-Preserving Mapping", "Prompt File Naming"
- Reference: `nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`

## Preconditions

- `nl_processing/core/prompts.py` and `load_prompt()` work
- `nl_processing/core/models.py` provides `TranslationResult`

## Non-goals

- Service class implementation (T2), testing (T3-T5)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/translate_word/prompts/generate_nl_ru_prompt.py` -- create
- `nl_processing/translate_word/prompts/nl_ru.json` -- create (generated artifact)

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/`, other modules, test files, `service.py`

**Test scope:**
- No tests. Verify by running generation script.

## Touched surface (expected files / modules)

- `nl_processing/translate_word/prompts/generate_nl_ru_prompt.py` -- new
- `nl_processing/translate_word/prompts/nl_ru.json` -- new (generated)

## Dependencies and sequencing notes

- No dependencies. First task.
- T2 depends on this producing a valid `nl_ru.json`.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-core` (>=0.3)
  - **Same patterns** as the other sprints' T1 tasks: `ChatPromptTemplate.from_messages()`, `dumpd()`, `SystemMessage`, `HumanMessage`, `AIMessage` with `tool_calls`, `ToolMessage`, `MessagesPlaceholder`.
  - **Key difference**: The wrapper model needs to return a list of `TranslationResult` objects, and the prompt must enforce one-to-one order-preserving mapping.

## Implementation steps (developer-facing)

1. **Create directory** `nl_processing/translate_word/prompts/` (if not exists).

2. **Create `generate_nl_ru_prompt.py`** with:

   a. **System instruction** (in Russian):
      - You are a professional translator from Dutch to Russian
      - You receive a list of Dutch words/phrases and must translate each one to Russian
      - Return exactly one translation per input word, in the same order
      - The number of translations in the output must equal the number of words in the input
      - Each translation should be the most common, natural Russian equivalent
      - If the input list is empty, return an empty list

   b. **Internal wrapper Pydantic model**:
      ```python
      from pydantic import BaseModel
      from nl_processing.core.models import TranslationResult

      class _TranslationBatch(BaseModel):
          translations: list[TranslationResult]
      ```

   c. **Few-shot examples** (3-4 pairs):

      - **Example 1** (3 simple words):
        - Input: `"huis, lopen, snel"`  (or as a formatted list)
        - Output: `{"translations": [{"translation": "дом"}, {"translation": "ходить"}, {"translation": "быстро"}]}`

      - **Example 2** (5 words with articles/normalized forms):
        - Input: `"de kat, het boek, schrijven, mooi, in"`
        - Output: `{"translations": [{"translation": "кошка"}, {"translation": "книга"}, {"translation": "писать"}, {"translation": "красивый"}, {"translation": "в"}]}`

      - **Example 3** (compound expression):
        - Input: `"er vandoor gaan, de fiets"`
        - Output: `{"translations": [{"translation": "сбежать"}, {"translation": "велосипед"}]}`

      - **Example 4** (empty list):
        - Input: `""`
        - Output: `{"translations": []}`

   d. **Input format**: The user message will contain the word list as a comma-separated or newline-separated string. The prompt must be clear about input format.

   e. **`MessagesPlaceholder(variable_name="text")`** as the final placeholder.

   f. **Serialize** with `dumpd()` and save to `nl_ru.json`.

3. **Run the generation script**: `uv run python nl_processing/translate_word/prompts/generate_nl_ru_prompt.py`

4. **Verify** the JSON loads successfully.

5. **File under 200 lines**.

## Production safety constraints (mandatory)

- N/A -- static file generation.

## Anti-disaster constraints (mandatory)

- Follow reference prompt generation pattern.
- Ensure Russian translations are linguistically accurate.

## Error handling + correctness rules (mandatory)

- Generation script fails clearly on error.

## Zero legacy tolerance rule (mandatory)

- New files only.

## Acceptance criteria (testable)

1. `generate_nl_ru_prompt.py` exists and is executable
2. `nl_ru.json` exists after running the script
3. `load_prompt("nl_processing/translate_word/prompts/nl_ru.json")` succeeds
4. Prompt demonstrates one-to-one mapping in few-shot examples
5. Prompt demonstrates empty-list handling
6. Generation script under 200 lines
7. Ruff passes

## Verification / quality gates

- [ ] Generation script runs without error
- [ ] `nl_ru.json` loadable
- [ ] Ruff passes
- [ ] Pylint 200-line limit passes
- [ ] Russian translations are correct

## Edge cases

- The wrapper model `_TranslationBatch` name must match between generation script and T2's service
- Input format (how words are passed to the LLM) must be consistent between prompt examples and service implementation

## Notes / risks

- **Risk**: Input format mismatch between prompt examples and how T2 passes words.
  - **Mitigation**: Coordinate with T2. Use a clear, consistent format (e.g., newline-separated or comma-separated).
- **Decision made autonomously**: Using `_TranslationBatch` with `translations: list[TranslationResult]` as the wrapper model.
