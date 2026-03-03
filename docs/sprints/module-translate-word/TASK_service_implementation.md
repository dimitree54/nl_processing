---
Task ID: `T2`
Title: `Implement WordTranslator class, replacing legacy stub`
Sprint: `2026-03-03_translate-word`
Module: `translate_word`
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

A fully functional `WordTranslator` class exists in `service.py`, replacing the legacy `translate_word` function and `_TRANSLATIONS` dictionary. The class sends all input words in a single LLM call, returns `list[TranslationResult]` with one-to-one order-preserving mapping, handles empty input without API calls, and wraps API errors.

## Context (contract mapping)

- Requirements: `nl_processing/translate_word/docs/prd_translate_word.md` -- FR1-FR9, NFR1-NFR2
- Architecture: `nl_processing/translate_word/docs/architecture_translate_word.md` -- "Single LLM Call Per Batch", "One-to-One Order-Preserving Mapping", "Source + Target Language Constructor", "Empty List for Empty Input"
- Shared architecture: `docs/planning-artifacts/architecture.md` -- "Module Public Interface Pattern", "Error Handling Pattern"
- Reference: `nl_processing/extract_text_from_image/service.py`

## Preconditions

- T1 completed: `nl_processing/translate_word/prompts/nl_ru.json` exists
- Core package provides `Language`, `TranslationResult`, `APIError`, `load_prompt()`

## Non-goals

- Tests (T3-T5), prompt tuning, vulture cleanup (T6)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/translate_word/service.py` -- replace entirely

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/`, other modules, test files, prompt files

**Test scope:**
- No tests in this task. Manual verification in REPL.

## Touched surface (expected files / modules)

- `nl_processing/translate_word/service.py` -- complete replacement

## Dependencies and sequencing notes

- Depends on T1 for prompt JSON.
- T3-T6 depend on this.
- Must coordinate with T1 on wrapper model name and input format.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-openai` (>=0.3)
  - Same patterns as other sprints: `ChatOpenAI.bind_tools()`, `tool_choice`, `ainvoke()`, `tool_calls[0]["args"]`.
- **Key difference from other modules**: The input is a `list[str]` (word list) that must be formatted into a single prompt message. The output wrapper must contain `list[TranslationResult]`.

## Implementation steps (developer-facing)

1. **Delete the entire contents of `service.py`** -- remove legacy `translate_word` function, `_TRANSLATIONS` dict.

2. **Define internal wrapper model**:
   ```python
   from pydantic import BaseModel
   from nl_processing.core.models import TranslationResult

   class _TranslationBatch(BaseModel):
       translations: list[TranslationResult]
   ```

3. **Define supported language pairs**:
   ```python
   _SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}
   ```

4. **Implement `WordTranslator` class**:

   ```python
   import pathlib
   from langchain_core.messages import HumanMessage
   from langchain_openai import ChatOpenAI
   from nl_processing.core.exceptions import APIError
   from nl_processing.core.models import Language, TranslationResult
   from nl_processing.core.prompts import load_prompt

   _PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

   class WordTranslator:
       """Translate word batches between languages.

       Usage:
           translator = WordTranslator(
               source_language=Language.NL,
               target_language=Language.RU,
           )
           results = await translator.translate(["huis", "lopen"])
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
               [_TranslationBatch],
               tool_choice=_TranslationBatch.__name__,
           )
           self._chain = prompt | llm

       async def translate(
           self, words: list[str]
       ) -> list[TranslationResult]:
           """Translate a list of words from source to target language.

           Returns one TranslationResult per input word, in the same order.
           Returns empty list for empty input (no API call).
           """
           if not words:
               return []

           # Format words as input for the prompt
           word_text = "\n".join(words)

           try:
               response = await self._chain.ainvoke(
                   {"text": [HumanMessage(content=word_text)]}
               )
               result = _TranslationBatch(
                   **response.tool_calls[0]["args"]  # type: ignore[attr-defined]
               )
           except Exception as e:
               raise APIError(str(e)) from e

           return result.translations
   ```

5. **Key design decisions**:
   - `source_language` and `target_language` are both **required** (same pattern as `TextTranslator`).
   - Language pair validation at init -- fail fast.
   - Empty input returns empty list **without** API call.
   - Words formatted as newline-separated text in the `HumanMessage`. This must match the prompt examples from T1.
   - Single LLM call per batch (TW-NFR2).
   - The `_TranslationBatch.translations` field contains the list of `TranslationResult` objects.

6. **File under 200 lines**.

## Production safety constraints (mandatory)

- N/A.

## Anti-disaster constraints (mandatory)

- Follow `ImageTextExtractor` and `TextTranslator` patterns.
- All from `pyproject.toml`.

## Error handling + correctness rules (mandatory)

- **ValueError at init** for unsupported pairs (configuration error).
- **APIError wrapping** for chain invocation failures.
- **No silenced errors**.
- **Empty list for empty input** -- no API call, no error.

## Zero legacy tolerance rule (mandatory)

- Legacy `translate_word(word: str, target_language: str) -> str` function **deleted entirely**.
- Legacy `_TRANSLATIONS` dictionary **deleted entirely**.
- No backward-compatible wrapper.

## Acceptance criteria (testable)

1. `service.py` contains `WordTranslator` class
2. Constructor requires `source_language` and `target_language`
3. Constructor accepts optional `model` parameter
4. Constructor raises `ValueError` for unsupported pairs
5. `translate(words: list[str]) -> list[TranslationResult]` is async
6. Empty input returns empty list without API call
7. Single API call for entire batch (verified by code inspection)
8. Legacy function and `_TRANSLATIONS` dict deleted
9. Ruff passes, file under 200 lines

## Verification / quality gates

- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] Legacy code removed (function + dict)
- [ ] All public methods have type hints and docstrings

## Edge cases

- One-to-one mapping enforcement: the prompt instructs the LLM, the Pydantic schema enforces the list structure, but the exact count is not enforced at the code level. Tests (T4) will validate this.
- Input format: words joined by `"\n"`. Must match T1's prompt examples.
- `_TranslationBatch.__name__` evaluates to `"_TranslationBatch"` -- must match T1's few-shot examples.

## Notes / risks

- **Decision made autonomously**: Using `gpt-4.1-mini` as default model (matching reference).
- **Decision made autonomously**: Using `ValueError` for unsupported pairs (same as `TextTranslator`).
- **Decision made autonomously**: Words formatted as newline-separated text. This is a simple, unambiguous format for the LLM.
