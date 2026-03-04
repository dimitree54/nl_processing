---
Task ID: `T2`
Title: `Implement WordExtractor class, replacing legacy regex stub`
Sprint: `2026-03-03_extract-words-from-text`
Module: `extract_words_from_text`
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `done`
---

## Goal / value

A fully functional `WordExtractor` class exists in `service.py`, replacing the legacy `extract_words_from_text` regex stub. The class follows the exact same pattern as `ImageTextExtractor` from the reference implementation: constructor builds a LangChain chain with tool binding, `extract()` method invokes the chain and returns `list[WordEntry]`.

## Context (contract mapping)

- Requirements: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md` -- FR1-FR11, NFR1-NFR2
- Architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md` -- "Module Internal Structure", "Empty List for Non-Target Language"
- Shared architecture: `docs/planning-artifacts/architecture.md` -- "Module Public Interface Pattern", "Error Handling Pattern", "Each Module Instantiates Its Own ChatOpenAI"
- Reference implementation: `nl_processing/extract_text_from_image/service.py`

## Preconditions

- T1 completed: `nl_processing/extract_words_from_text/prompts/nl.json` exists and is loadable
- `nl_processing/core/models.py` provides `WordEntry`, `Language`
- `nl_processing/core/exceptions.py` provides `APIError`
- `nl_processing/core/prompts.py` provides `load_prompt()`

## Non-goals

- Writing tests (that's T3, T4, T5)
- Prompt tuning (that's part of T4 iteration)
- Updating vulture whitelist (that's T6)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/extract_words_from_text/service.py` -- replace entirely

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/extract_text_from_image/` -- other module
- `nl_processing/translate_text/`, `nl_processing/translate_word/` -- other modules
- Any test files
- Prompt files (already created in T1)

**Test scope:**
- No tests created in this task.
- Manual verification: instantiate the class in a Python REPL and confirm it initializes without error.

## Touched surface (expected files / modules)

- `nl_processing/extract_words_from_text/service.py` -- complete replacement

## Dependencies and sequencing notes

- Depends on T1 for the prompt JSON file.
- T3, T4, T5, T6 all depend on this task.
- Must coordinate with T1 on the wrapper model name used in `bind_tools()` matching the tool name in few-shot prompt examples.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-openai` (version >=0.3, per `pyproject.toml`)
  - **API reference**: `ChatOpenAI` class -- `langchain_openai.ChatOpenAI`
  - **`bind_tools()` method**: https://python.langchain.com/docs/how_to/tool_calling/
  - **Usage pattern** (from reference `extract_text_from_image/service.py`):
    ```python
    llm = ChatOpenAI(model=model, temperature=0).bind_tools(
        [PydanticModel], tool_choice=PydanticModel.__name__
    )
    chain = prompt | llm
    response = await chain.ainvoke(input_dict)
    result = PydanticModel(**response.tool_calls[0]["args"])
    ```
  - **Known gotchas**:
    - `bind_tools()` takes a list of Pydantic models. `tool_choice` forces the LLM to use that specific tool.
    - Response parsing: `response.tool_calls[0]["args"]` returns a dict matching the Pydantic model fields.
    - The `type: ignore[attr-defined]` comment is needed for `tool_calls` attribute access on the response (see reference).

- **Library**: `langchain-core` (version >=0.3)
  - **`MessagesPlaceholder`**: Used in the prompt template to inject the user's input text.
  - **`HumanMessage`**: The user input will be wrapped in a `HumanMessage` with text content.

## Implementation steps (developer-facing)

1. **Delete the entire contents of `service.py`** -- remove the legacy `extract_words_from_text` function and the regex import. This is the zero-legacy-tolerance rule.

2. **Define the internal wrapper model** at module level:
   ```python
   from pydantic import BaseModel
   from nl_processing.core.models import WordEntry

   class _WordList(BaseModel):
       words: list[WordEntry]
   ```
   This wrapper is needed because `bind_tools()` takes a single Pydantic model, but the output is a list. The prompt few-shot examples (from T1) must use the same model name.

3. **Implement `WordExtractor` class** following the exact pattern from `ImageTextExtractor`:

   ```python
   import pathlib
   from langchain_openai import ChatOpenAI
   from nl_processing.core.exceptions import APIError
   from nl_processing.core.models import Language, WordEntry
   from nl_processing.core.prompts import load_prompt

   _PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

   class WordExtractor:
       """Extract and normalize words from markdown text.

       Usage:
           extractor = WordExtractor()
           words = await extractor.extract(text)
       """

       def __init__(
           self,
           *,
           language: Language = Language.NL,
           model: str = "gpt-4.1-mini",
       ) -> None:
           self._language = language
           prompt_path = str(_PROMPTS_DIR / f"{language.value}.json")
           prompt = load_prompt(prompt_path)

           llm = ChatOpenAI(model=model, temperature=0).bind_tools(
               [_WordList], tool_choice=_WordList.__name__
           )
           self._chain = prompt | llm

       async def extract(self, text: str) -> list[WordEntry]:
           """Extract and normalize words from the given text.

           Returns a list of WordEntry objects with normalized forms and types.
           Returns an empty list if no words in the target language are found.
           """
           try:
               response = await self._chain.ainvoke({"text": [HumanMessage(content=text)]})
               result = _WordList(**response.tool_calls[0]["args"])
           except Exception as e:
               raise APIError(str(e)) from e

           return result.words
   ```

4. **Key design decisions**:
   - The `extract()` method is `async` (matches reference pattern using `ainvoke`).
   - The input text is wrapped in a `HumanMessage` and passed via `MessagesPlaceholder(variable_name="text")`.
   - Empty list for non-target language: the LLM is instructed via prompt to return an empty `words` list. No post-processing needed.
   - All exceptions from the chain invocation are wrapped in `APIError`.
   - The `type: ignore[attr-defined]` comment may be needed on `response.tool_calls`.

5. **Verify the file is under 200 lines** (pylint limit).

6. **Verify ruff compliance**: no relative imports, no `os.getenv`, empty `__init__.py` unchanged, all type hints present.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: N/A -- no local resources used.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the exact pattern from `ImageTextExtractor`. Do not invent a new pattern.
- **Correct libraries only**: `langchain-openai` (>=0.3), `langchain-core` (>=0.3), `pydantic` (>=2.0) -- all from `pyproject.toml`.
- **Correct file locations**: `nl_processing/extract_words_from_text/service.py` per architecture spec.
- **No regressions**: The legacy stub is completely replaced. No backward compatibility needed (zero-legacy policy).

## Error handling + correctness rules (mandatory)

- **APIError wrapping**: `try/except Exception as e: raise APIError(str(e)) from e` -- matches reference pattern exactly.
- **No silenced errors**: No empty catch blocks, no default fallbacks.
- **Chain from `e`**: Always use `from e` to preserve the exception chain.

## Zero legacy tolerance rule (mandatory)

After implementing this task:
- The legacy `extract_words_from_text` function is **deleted** entirely.
- The `import re` and `_WORD_RE` regex pattern are **deleted** entirely.
- No backward-compatible wrapper or alias is maintained.

## Acceptance criteria (testable)

1. `nl_processing/extract_words_from_text/service.py` contains `WordExtractor` class
2. `WordExtractor` has `__init__` with keyword-only `language` and `model` params with defaults
3. `WordExtractor.extract(text: str) -> list[WordEntry]` is an async method
4. The legacy `extract_words_from_text` function no longer exists
5. The `import re` and `_WORD_RE` regex pattern no longer exist
6. The class uses `ChatOpenAI.bind_tools()` with a wrapper Pydantic model
7. The class loads the prompt via `core.prompts.load_prompt()`
8. All exceptions from chain invocation are wrapped as `APIError`
9. `uv run ruff check nl_processing/extract_words_from_text/service.py` passes
10. `uv run ruff format --check nl_processing/extract_words_from_text/service.py` passes
11. File is under 200 lines

## Verification / quality gates

- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] No relative imports
- [ ] All public methods have type hints and docstrings
- [ ] Legacy function completely removed
- [ ] Constructor pattern matches reference (keyword-only, defaults)
- [ ] Error handling pattern matches reference (`APIError` wrapping)

## Edge cases

- The `_WordList` wrapper model must be defined in `service.py` (not imported from core -- it's an internal model)
- If the prompt placeholder variable name doesn't match between `generate_nl_prompt.py` and `service.py`, the chain will fail silently. Ensure both use `"text"` as the variable name.
- The `tool_choice` parameter must use `_WordList.__name__` which evaluates to `"_WordList"` -- this must match the tool name in the few-shot examples from T1.

## Notes / risks

- **Risk**: Wrapper model name `_WordList` has a leading underscore. `bind_tools` uses `__name__` which includes the underscore. The few-shot examples in T1 must use the same name.
  - **Mitigation**: Verify consistency between T1 and T2 during implementation. If naming conflicts arise, rename to `WordList` (without underscore) in both places.
- **Decision made autonomously**: Using `gpt-4.1-mini` as default model (matching the reference implementation) rather than `gpt-5-nano` from the PRD. The PRD says "baseline evaluation starts from GPT-5 Mini, then downgrades to cheapest model that passes quality gates." The reference implementation already settled on `gpt-4.1-mini`. Follow the established pattern.
