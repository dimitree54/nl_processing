---
Task ID: `T2`
Title: `Implement TextTranslator class, replacing legacy stub`
Sprint: `2026-03-03_translate-text`
Module: `translate_text`
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

A fully functional `TextTranslator` class exists in `service.py`, replacing the legacy `translate_text` function. The class uses LangChain tool calling for structured output, validates language pairs at init time, handles empty/non-Dutch input by returning empty string, and wraps API errors as `APIError`.

## Context (contract mapping)

- Requirements: `nl_processing/translate_text/docs/prd_translate_text.md` -- FR1-FR10, NFR1-NFR2
- Architecture: `nl_processing/translate_text/docs/architecture_translate_text.md` -- "Source + Target Language Constructor", "Returns Plain str", "Empty String for Edge Cases", "Language Pair Validation at Init Time"
- Shared architecture: `docs/planning-artifacts/architecture.md` -- "Module Public Interface Pattern", "Error Handling Pattern"
- Reference: `nl_processing/extract_text_from_image/service.py`

## Preconditions

- T1 completed: `nl_processing/translate_text/prompts/nl_ru.json` exists
- Core package provides `Language`, `APIError`, `load_prompt()`

## Non-goals

- Tests (T3, T4, T5)
- Prompt tuning
- Vulture cleanup (T6)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/translate_text/service.py` -- replace entirely

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/`, other modules, test files, prompt files

**Test scope:**
- No tests in this task. Manual verification: instantiate class in REPL.

## Touched surface (expected files / modules)

- `nl_processing/translate_text/service.py` -- complete replacement

## Dependencies and sequencing notes

- Depends on T1 for prompt JSON.
- T3, T4, T5, T6 depend on this task.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-openai` (>=0.3)
  - **`ChatOpenAI.bind_tools()`**: Bind Pydantic model as tool for structured output.
  - **`tool_choice`**: Force the LLM to use the specific tool.
  - **Response parsing**: `response.tool_calls[0]["args"]` to extract the model fields.
- **Pattern**: Same as `ImageTextExtractor` -- `prompt | llm` chain, `ainvoke()`, tool_calls parsing.

## Implementation steps (developer-facing)

1. **Delete the entire contents of `service.py`** -- remove legacy `translate_text` function.

2. **Define internal wrapper model**:
   ```python
   from pydantic import BaseModel

   class _TranslatedText(BaseModel):
       text: str
   ```

3. **Define supported language pairs** as a module-level constant:
   ```python
   _SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}
   ```

4. **Implement `TextTranslator` class**:

   ```python
   import pathlib
   from langchain_core.messages import HumanMessage
   from langchain_openai import ChatOpenAI
   from nl_processing.core.exceptions import APIError
   from nl_processing.core.models import Language
   from nl_processing.core.prompts import load_prompt

   _PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

   class TextTranslator:
       """Translate text between languages with markdown preservation.

       Usage:
           translator = TextTranslator(
               source_language=Language.NL,
               target_language=Language.RU,
           )
           result = await translator.translate(dutch_text)
       """

       def __init__(
           self,
           *,
           source_language: Language,
           target_language: Language,
           model: str = "gpt-4.1-mini",
       ) -> None:
           pair = (source_language.value, target_language.value)
           if pair not in _SUPPORTED_PAIRS:
               msg = (
                   f"Unsupported language pair: "
                   f"{source_language.value} -> {target_language.value}. "
                   f"Supported pairs: {_SUPPORTED_PAIRS}"
               )
               raise ValueError(msg)

           self._source_language = source_language
           self._target_language = target_language

           prompt_file = f"{source_language.value}_{target_language.value}.json"
           prompt_path = str(_PROMPTS_DIR / prompt_file)
           prompt = load_prompt(prompt_path)

           llm = ChatOpenAI(model=model, temperature=0).bind_tools(
               [_TranslatedText], tool_choice=_TranslatedText.__name__
           )
           self._chain = prompt | llm

       async def translate(self, text: str) -> str:
           """Translate text from source to target language.

           Returns the translated text or empty string for empty/non-source input.
           """
           if not text.strip():
               return ""

           try:
               response = await self._chain.ainvoke(
                   {"text": [HumanMessage(content=text)]}
               )
               result = _TranslatedText(
                   **response.tool_calls[0]["args"]  # type: ignore[attr-defined]
               )
           except Exception as e:
               raise APIError(str(e)) from e

           return result.text
   ```

5. **Key design decisions**:
   - `source_language` and `target_language` are both **required** (not optional with defaults). This differs from single-language modules.
   - Language pair validation at `__init__` time -- fail fast per architecture decision.
   - Empty string input returns empty string **without** making an API call (checked before `ainvoke`).
   - Returns plain `str`, not a Pydantic model -- per architecture decision.
   - The `_TranslatedText` wrapper ensures structured output (no LLM chatter).

6. **File must be under 200 lines**.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the `ImageTextExtractor` pattern exactly.
- **Correct libraries only**: All from `pyproject.toml`.
- **No regressions**: Legacy stub completely replaced.

## Error handling + correctness rules (mandatory)

- **ValueError at init**: Clear message for unsupported language pairs. Not `APIError` -- this is a configuration error, not an API failure.
- **APIError wrapping**: `try/except Exception as e: raise APIError(str(e)) from e` for chain invocation.
- **No silenced errors**: No empty catch blocks.
- **Empty string check before API call**: `if not text.strip(): return ""` -- avoids unnecessary API call.

## Zero legacy tolerance rule (mandatory)

- Legacy `translate_text(text: str, target_language: str) -> str` function **deleted entirely**.
- No backward-compatible wrapper.

## Acceptance criteria (testable)

1. `service.py` contains `TextTranslator` class
2. Constructor requires `source_language` and `target_language` (both mandatory)
3. Constructor accepts optional `model` parameter
4. Constructor raises `ValueError` for unsupported language pairs
5. `translate(text: str) -> str` is async
6. Empty/whitespace input returns empty string without API call
7. Legacy `translate_text` function no longer exists
8. All exceptions wrapped as `APIError`
9. Ruff passes, file under 200 lines

## Verification / quality gates

- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] Legacy function removed
- [ ] All public methods have type hints and docstrings

## Edge cases

- The `_TranslatedText.__name__` evaluates to `"_TranslatedText"` -- must match the tool name in T1's few-shot examples.
- Non-Dutch text handling: the prompt instructs the LLM to return empty string, and the `_TranslatedText.text` field will contain `""`. This is returned as-is.

## Notes / risks

- **Decision made autonomously**: Using `gpt-4.1-mini` as default model (matching the reference implementation).
- **Decision made autonomously**: Using `ValueError` (not a custom exception) for unsupported language pairs, because this is a developer configuration error, not a domain error. Architecture says "descriptive exception" but doesn't specify a custom type.
