---
Task ID: `T1`
Title: `Create Dutch word extraction prompt generation script and nl.json`
Sprint: `2026-03-03_extract-words-from-text`
Module: `extract_words_from_text`
Depends on: `--`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

A working Dutch word extraction prompt JSON file (`nl.json`) exists in the module's `prompts/` directory, loadable by `core.prompts.load_prompt()`, and a generation script (`generate_nl_prompt.py`) that can regenerate it. The prompt instructs the LLM to extract and normalize Dutch words from markdown text with flat word-type assignment.

## Context (contract mapping)

- Requirements: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md` -- FR1-FR11 (extraction, normalization, taxonomy)
- Architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md` -- "Language-Specific Normalization via Prompt", "Flat Word-Type Taxonomy", "Compound Expressions as Single Units"
- Shared architecture: `docs/planning-artifacts/architecture.md` -- "Prompt JSON Format", "Prompt File Organization"
- Reference implementation: `nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`

## Preconditions

- `nl_processing/core/prompts.py` exists and `load_prompt()` works with LangChain native serialization format
- `nl_processing/core/models.py` exists with `WordEntry` model (fields: `normalized_form: str`, `word_type: str`)
- LangChain and langchain-openai are installed (verified in `pyproject.toml`)

## Non-goals

- Testing the prompt quality (that's T4/T5)
- Implementing the service class (that's T2)
- Creating few-shot examples with real API calls (prompt includes text-based examples only, no images needed)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py` -- create
- `nl_processing/extract_words_from_text/prompts/nl.json` -- create (generated artifact)

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/extract_text_from_image/` -- other module
- `nl_processing/translate_text/`, `nl_processing/translate_word/` -- other modules
- Any test files
- `service.py` -- that's T2

**Test scope:**
- No tests created in this task. Prompt loadability is verified by running the generation script and confirming `load_prompt()` can deserialize the output.
- Verification command: `uv run python nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py`

## Touched surface (expected files / modules)

- `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py` -- new file
- `nl_processing/extract_words_from_text/prompts/nl.json` -- new file (generated)

## Dependencies and sequencing notes

- No dependencies. This is the first task.
- T2 (service implementation) depends on this task producing a valid `nl.json`.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-core` (version >=0.3, per `pyproject.toml`)
  - **Official documentation**: https://python.langchain.com/docs/concepts/prompt_templates/
  - **API reference**: `langchain_core.prompts.ChatPromptTemplate`, `langchain_core.load.dumpd()`, `langchain_core.messages.SystemMessage`, `langchain_core.messages.HumanMessage`, `langchain_core.messages.AIMessage`, `langchain_core.messages.ToolMessage`
  - **Usage pattern** (verified from reference implementation `generate_nl_prompt.py`):
    ```python
    from langchain_core.load import dumpd
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="..."),
        HumanMessage(content="example input"),
        AIMessage(content="", tool_calls=[{"name": "WordEntry", "args": {...}, "id": "call_1"}]),
        ToolMessage(content="...", tool_call_id="call_1"),
        MessagesPlaceholder(variable_name="text"),
    ])
    data = dumpd(prompt)
    json.dump(data, f, indent=2)
    ```
  - **Known gotchas**: The `dumpd()` function produces a dict with `"lc"`, `"type"`, `"id"` keys. The `load()` function in `core.prompts` expects this exact format. `tool_calls` in `AIMessage` must include `"name"`, `"args"`, and `"id"` fields.

## Implementation steps (developer-facing)

1. Create directory `nl_processing/extract_words_from_text/prompts/` (if not exists).

2. Create `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py` following the reference pattern from `nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`:

   a. Define a system instruction in Dutch that tells the LLM to:
      - Extract all Dutch words from the provided markdown text
      - Ignore markdown formatting (headings, bold, italic, lists) -- extract only linguistic content
      - Ignore text in other languages
      - Normalize each word according to Dutch rules:
        - Nouns: include article (de/het), e.g., "de fiets", "het huis"
        - Verbs: infinitive form, e.g., "lopen", "hebben"
        - Adjectives, prepositions, conjunctions: base form
        - Proper nouns (persons): as-is with type "proper_noun_person"
        - Proper nouns (countries): as-is with type "proper_noun_country"
      - Extract compound expressions and phrasal constructs as single units
      - Assign a flat word type to each word (noun, verb, adjective, preposition, conjunction, proper_noun_person, proper_noun_country, adverb, numeral, pronoun, article, etc.)
      - Return the result as a list of WordEntry objects

   b. Create 3-5 few-shot examples as `HumanMessage` + `AIMessage` (with `tool_calls`) + `ToolMessage` triplets:
      - Example 1: Simple sentence with noun (de/het), verb, adjective -- e.g., "De grote kat loopt snel."
      - Example 2: Sentence with proper nouns, prepositions -- e.g., "Jan woont in Nederland."
      - Example 3: Sentence with compound expression -- e.g., "Zij gaat er vandoor."
      - Example 4: Non-Dutch text -- returns empty tool_calls list (demonstrates empty list behavior)
      - Example 5: Mixed markdown with various word types

   c. Use `MessagesPlaceholder(variable_name="text")` as the final placeholder for user input.

   d. **Important**: Since `WordEntry` is a flat model and the LLM needs to return a list, the tool calling approach must use a wrapper model. Define an internal `_WordList` Pydantic model with `words: list[WordEntry]` field, and use that as the tool schema. The `AIMessage.tool_calls` in few-shot examples must use `_WordList` as the tool name with `{"words": [...]}` as args.

   e. Serialize with `dumpd()` and save to `nl.json`.

3. Run the generation script: `uv run python nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py`

4. Verify the generated `nl.json` can be loaded:
   ```python
   from nl_processing.core.prompts import load_prompt
   prompt = load_prompt("nl_processing/extract_words_from_text/prompts/nl.json")
   ```

5. Ensure the generation script is under 200 lines (pylint limit).

## Production safety constraints (mandatory)

- **Database operations**: N/A -- no database involved.
- **Resource isolation**: N/A -- script generates a static JSON file only.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuse the exact prompt generation pattern from `extract_text_from_image/prompts/generate_nl_prompt.py`. Do not invent a new pattern.
- **Correct libraries only**: `langchain-core` (>=0.3, from `pyproject.toml`).
- **Correct file locations**: `nl_processing/extract_words_from_text/prompts/` per architecture spec.
- **No regressions**: This task creates new files only; no existing files modified.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: The generation script should fail clearly if any step fails.
- **No mock fallbacks**: The prompt must contain real, linguistically accurate Dutch examples.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove in this task (new files only).

## Acceptance criteria (testable)

1. `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py` exists and is executable
2. `nl_processing/extract_words_from_text/prompts/nl.json` exists after running the script
3. `load_prompt("nl_processing/extract_words_from_text/prompts/nl.json")` returns a `ChatPromptTemplate` without error
4. The prompt contains a Dutch system instruction, at least 3 few-shot examples, and a `MessagesPlaceholder`
5. Few-shot examples demonstrate: noun normalization (de/het), verb normalization (infinitive), flat word types, compound expressions, and empty-list for non-Dutch text
6. The generation script is under 200 lines
7. `uv run ruff check nl_processing/extract_words_from_text/prompts/` passes
8. `uv run ruff format --check nl_processing/extract_words_from_text/prompts/` passes

## Verification / quality gates

- [ ] Generation script runs without error
- [ ] `nl.json` is loadable by `core.prompts.load_prompt()`
- [ ] Ruff format and check pass on the new files
- [ ] Pylint 200-line limit passes
- [ ] Few-shot examples are linguistically accurate Dutch

## Edge cases

- The wrapper model (`_WordList`) must be defined in the generation script (or in `service.py` -- but since T2 hasn't been created yet, define it locally in the script for now; T2 will define the canonical version)
- Ensure the `tool_calls` in few-shot `AIMessage` examples use the correct wrapper model name that matches what `bind_tools()` will produce in T2

## Notes / risks

- **Risk**: Mismatch between the tool name used in few-shot examples and the actual name from `bind_tools()` in T2.
  - **Mitigation**: The tool name in `bind_tools()` comes from the Pydantic model's `__name__`. Ensure both the generation script and the service use the same wrapper model name. Coordinate with T2.
- **Decision made autonomously**: Using `_WordList` wrapper model because `bind_tools` needs a single Pydantic model, but the output is a list of `WordEntry`. This matches how the reference implementation uses `ExtractedText` as a wrapper.
