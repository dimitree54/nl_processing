---
Task ID: T2
Title: Migrate extract_words_from_text to use Word model
Sprint: 2026-03-04_unified-word-model
Module: extract_words_from_text
Depends on: T1
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Migrate the `extract_words_from_text` module from returning `list[WordEntry]` to returning `list[Word]`. Update the internal LLM schema to use `PartOfSpeech` Enum. Update all few-shot examples in the prompt generator. Regenerate the prompt JSON. Update all tests (unit, integration, e2e). After this task, `WordEntry` is no longer imported anywhere in this module.

## Context (contract mapping)

- Architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md` -- "Flat Word-Type Taxonomy" decision (will change from strings to Enum)
- PRD: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md` -- FR9: "Each WordEntry contains a normalized form and a word type"
- Current service: `nl_processing/extract_words_from_text/service.py` -- returns `list[WordEntry]`
- Current prompt generator: `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py`

## Preconditions

- T1 completed: `PartOfSpeech` Enum and `Word` model exist in `nl_processing/core/models.py`
- All existing tests still pass

## Non-goals

- Do NOT remove `WordEntry` from `core/models.py` (that is T4)
- Do NOT touch `translate_word` module (that is T3)
- Do NOT touch `translate_text` or `extract_text_from_image`
- Do NOT modify the system instruction text in the prompt (only the few-shot examples and the internal model)
- Do NOT change the LLM's output format -- it still returns `{normalized_form, word_type}` dicts. The change is: `word_type` is now validated as `PartOfSpeech` Enum instead of free-form string.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/extract_words_from_text/service.py`
- `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py`
- `nl_processing/extract_words_from_text/prompts/nl.json` (regenerated)
- `tests/unit/extract_words_from_text/test_word_extractor.py`
- `tests/unit/extract_words_from_text/conftest.py`
- `tests/unit/extract_words_from_text/test_error_handling.py`
- `tests/integration/extract_words_from_text/test_extraction_accuracy.py`
- `tests/e2e/extract_words_from_text/test_full_extraction.py`
- `tests/e2e/extract_words_from_text/test_real_text_quality.py`

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/models.py` (already done in T1)
- `nl_processing/translate_word/` (any file)
- `nl_processing/translate_text/` (any file)
- `nl_processing/extract_text_from_image/` (any file)
- `nl_processing/database/` (any file)
- Any test files not listed above
- `vulture_whitelist.py` (no changes expected)

**Test scope:**
- Unit: `uv run pytest tests/unit/core/ tests/unit/extract_words_from_text/ -x -v`
- Integration + e2e: `doppler run -- uv run pytest tests/integration/extract_words_from_text/ tests/e2e/extract_words_from_text/ -x -v`

## Touched surface (expected files / modules)

- `nl_processing/extract_words_from_text/service.py` -- change return type, update internal model
- `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py` -- update few-shot example helper
- `nl_processing/extract_words_from_text/prompts/nl.json` -- regenerated artifact
- `tests/unit/extract_words_from_text/test_word_extractor.py` -- update assertions
- `tests/unit/extract_words_from_text/conftest.py` -- update mock response type hints
- `tests/integration/extract_words_from_text/test_extraction_accuracy.py` -- update type assertions
- `tests/e2e/extract_words_from_text/test_full_extraction.py` -- update type assertions
- `tests/e2e/extract_words_from_text/test_real_text_quality.py` -- update set comparison

## Dependencies and sequencing notes

- Depends on T1: needs `PartOfSpeech` and `Word` in `core/models.py`
- Must be completed before T3: `translate_word` migration depends on `extract_words_from_text` using `Word` (since T3 changes translator input from `list[str]` to `list[Word]`)

## Implementation steps (developer-facing)

### Step 1: Update `nl_processing/extract_words_from_text/service.py`

#### 1a. Change imports

Replace:
```python
from nl_processing.core.models import Language, WordEntry
```
With:
```python
from nl_processing.core.models import Language, PartOfSpeech, Word
```

#### 1b. Replace `_WordList` internal model

The current internal model:
```python
class _WordList(BaseModel):
    """Internal wrapper: bind_tools needs a single model, output is a list."""
    words: list[WordEntry]
```

Replace with an internal LLM-facing model that does NOT include `language` (the LLM should not set it):

```python
class _LLMWordEntry(BaseModel):
    """Single word as returned by the LLM (no language field)."""
    normalized_form: str
    word_type: PartOfSpeech


class _WordList(BaseModel):
    """Internal wrapper: bind_tools needs a single model, output is a list."""
    words: list[_LLMWordEntry]
```

**Why `_LLMWordEntry` instead of `Word`?** The `Word` model has a `language` field that the LLM should not set. The LLM returns `{normalized_form, word_type}` and the service adds `language` programmatically.

#### 1c. Update `extract()` method signature and body

Change the return type annotation from `list[WordEntry]` to `list[Word]`:

```python
async def extract(self, text: str) -> list[Word]:
    """Extract and normalize words from the given text.

    Returns a list of Word objects with normalized forms, types, and language.
    Returns an empty list if no words in the target language are found.
    """
    try:
        response = await self._chain.ainvoke({"text": [HumanMessage(content=text)]})
        result = _WordList(**response.tool_calls[0]["args"])  # type: ignore[attr-defined]
    except Exception as e:
        raise APIError(str(e)) from e

    return [
        Word(
            normalized_form=entry.normalized_form,
            word_type=entry.word_type,
            language=self._language,
        )
        for entry in result.words
    ]
```

The key change: instead of returning `result.words` directly (which were `WordEntry` objects), we now map each `_LLMWordEntry` to a `Word` by adding `language=self._language`.

### Step 2: Update `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py`

The prompt generator's few-shot examples currently use `{"normalized_form": "...", "word_type": "..."}` dicts. The LLM output format stays the same (the LLM still returns these exact keys). However, the system instruction references `WordEntry` -- update it to reference the new internal model name.

#### 2a. Update the SYSTEM_INSTRUCTION string

Find this line in `SYSTEM_INSTRUCTION`:
```
"- Retourneer het resultaat als een lijst van WordEntry objecten in een _WordList wrapper.\n"
```

Replace with:
```
"- Retourneer het resultaat als een lijst van woord-objecten in een _WordList wrapper.\n"
```

This removes the reference to the now-unused `WordEntry` class name. The LLM doesn't need to know the Python class name.

#### 2b. No changes to `EXAMPLES`

The few-shot examples use `_w("de kat", "noun")` which produces `{"normalized_form": "de kat", "word_type": "noun"}`. This is still the correct format -- the LLM returns `{normalized_form, word_type}` and Pydantic coerces the string `"noun"` to `PartOfSpeech.NOUN` in `_LLMWordEntry`. **No changes needed to the examples themselves.**

### Step 3: Regenerate `nl.json`

Run the prompt generator:

```bash
uv run python nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py
```

This regenerates `nl_processing/extract_words_from_text/prompts/nl.json` with the updated system instruction.

### Step 4: Update unit tests

#### 4a. Update `tests/unit/extract_words_from_text/test_word_extractor.py`

**Change import:**
Replace:
```python
from nl_processing.core.models import Language, WordEntry
```
With:
```python
from nl_processing.core.models import Language, PartOfSpeech, Word
```

**Update `test_extract_happy_path`:**
- Change assertions from `result[0].word_type == "noun"` to `result[0].word_type == PartOfSpeech.NOUN`
- Change assertions from `result[1].word_type == "verb"` to `result[1].word_type == PartOfSpeech.VERB`
- Add assertion: `result[0].language == Language.NL`
- Add assertion: `result[1].language == Language.NL`

**Update `test_extract_returns_word_entry_objects`:**
- Rename to `test_extract_returns_word_objects`
- Change `isinstance(w, WordEntry)` to `isinstance(w, Word)`
- Change `assert w.word_type` to `assert isinstance(w.word_type, PartOfSpeech)`
- Add assertion: `assert w.language == Language.NL`

**Update `test_extract_invokes_chain_with_text`:**
- No changes needed (tests chain invocation structure, not return types)

**`test_extract_empty_list_for_non_target_language`:**
- No changes needed (empty list is still empty list)

**`test_constructor_defaults`, `test_constructor_custom_params`, `test_constructor_missing_prompt_file`:**
- No changes needed (constructor tests don't depend on return types)

#### 4b. Update `tests/unit/extract_words_from_text/conftest.py`

The `make_tool_response` function builds mock responses. The mock data format stays the same: `{"words": [{"normalized_form": "...", "word_type": "..."}]}`. The type hint can be updated for clarity:

No structural changes needed. The existing `make_tool_response` function produces dicts that are compatible with the new `_LLMWordEntry` model.

#### 4c. `tests/unit/extract_words_from_text/test_error_handling.py`

No changes needed. Error handling tests don't depend on return types -- they test that exceptions are wrapped as `APIError`.

### Step 5: Update integration tests

#### `tests/integration/extract_words_from_text/test_extraction_accuracy.py`

**Change import:**
Replace:
```python
from nl_processing.core.models import WordEntry
```
With:
```python
from nl_processing.core.models import Word
```

**Update `test_nouns_and_verbs`, `test_proper_nouns_and_prepositions`, `test_articles_and_adjectives`, `test_compound_expression`:**

These tests build expected sets as `{("de kat", "noun"), ...}` and compare against `{(w.normalized_form, w.word_type) for w in result}`.

With `PartOfSpeech` Enum, `w.word_type` is now `PartOfSpeech.NOUN` not `"noun"`. The set comparison will fail unless we extract the `.value`:

Change the set comprehension in the `actual` lines from:
```python
actual = {(w.normalized_form, w.word_type) for w in result}
```
To:
```python
actual = {(w.normalized_form, w.word_type.value) for w in result}
```

This applies to all 4 accuracy tests: `test_nouns_and_verbs`, `test_proper_nouns_and_prepositions`, `test_articles_and_adjectives`, `test_compound_expression`.

**Update `test_non_dutch_returns_empty`:**
No changes needed (empty list comparison).

**Update `test_performance_100_words`:**
Change:
```python
assert all(isinstance(w, WordEntry) for w in result)
```
To:
```python
assert all(isinstance(w, Word) for w in result)
```

### Step 6: Update e2e tests

#### `tests/e2e/extract_words_from_text/test_full_extraction.py`

**Change import:**
Replace:
```python
from nl_processing.core.models import WordEntry
```
With:
```python
from nl_processing.core.models import PartOfSpeech, Word
```

**Update `test_markdown_formatted_dutch_text`:**
Change `isinstance(w, WordEntry)` to `isinstance(w, Word)`.

**Update `test_full_pipeline_various_word_types`:**
Change `isinstance(w, WordEntry)` to `isinstance(w, Word)`.
Change `assert w.word_type, "word_type must not be empty"` to `assert isinstance(w.word_type, PartOfSpeech), "word_type must be PartOfSpeech"`.

**Update `test_non_dutch_text_returns_empty_list`:**
No changes needed.

**Update `test_mixed_markdown_with_compound_expressions`:**
Change `isinstance(w, WordEntry)` to `isinstance(w, Word)`.
Change `assert w.word_type, "word_type must not be empty"` to `assert isinstance(w.word_type, PartOfSpeech), "word_type must be PartOfSpeech"`.

**Update `test_all_results_have_valid_fields`:**
Change `isinstance(w, WordEntry)` to `isinstance(w, Word)`.
Change `assert isinstance(w.word_type, str), "word_type must be str"` to `assert isinstance(w.word_type, PartOfSpeech), "word_type must be PartOfSpeech"`.
Remove `assert len(w.word_type) > 0, "word_type must not be empty"` (redundant -- Enum value is always non-empty).

#### `tests/e2e/extract_words_from_text/test_real_text_quality.py`

**Update `_to_set` helper function:**
Change:
```python
def _to_set(words: list) -> set[tuple[str, str]]:
    return {(w.normalized_form, w.word_type) for w in words}
```
To:
```python
def _to_set(words: list) -> set[tuple[str, str]]:
    return {(w.normalized_form, w.word_type.value) for w in words}
```

The expected sets (`VOCABULARY_LIST_EXPECTED`, `ROTATED_VOCABULARY_EXPECTED`) remain as `set[tuple[str, str]]` with string word type values like `"noun"`, `"verb"` -- unchanged. The `_to_set` helper now extracts `.value` from the Enum to match.

### Step 7: Run all verification commands

```bash
# Unit tests (core + extract_words_from_text)
uv run pytest tests/unit/core/ tests/unit/extract_words_from_text/ -x -v

# Integration + e2e tests (requires API keys via Doppler)
doppler run -- uv run pytest tests/integration/extract_words_from_text/ tests/e2e/extract_words_from_text/ -x -v
```

**CRITICAL**: If integration or e2e tests fail due to LLM quality regression (not test code bugs), STOP and report to user. Do NOT loosen quality gates. Do NOT skip tests. Do NOT reduce assertion thresholds.

Then run the full check:

```bash
make check
```

## Production safety constraints (mandatory)

- **Database operations**: None. This task changes Python code only.
- **Resource isolation**: Integration/e2e tests make OpenAI API calls (paid). This is expected and uses the development Doppler environment, not production.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reusing `PartOfSpeech` and `Word` from core (created in T1). Using existing `_WordList` wrapper pattern, just changing its inner type.
- **Correct libraries only**: No new libraries. Using `pydantic.BaseModel` and `enum.Enum` already in project.
- **Correct file locations**: All changes in existing files. No new files created.
- **No regressions**: All existing test cases must still pass. The expected test values (word forms and types) are unchanged -- only the Python types differ.

## Error handling + correctness rules (mandatory)

- The `APIError` wrapping in `extract()` is unchanged.
- Pydantic validation in `_LLMWordEntry` will now reject invalid `word_type` strings that don't match `PartOfSpeech`. This is stricter than before (was free-form string) and is the CORRECT behavior -- invalid word types should fail fast.
- If the LLM returns a `word_type` value not in `PartOfSpeech`, the Pydantic validation error will be caught by the `except Exception` and re-raised as `APIError`. This is correct.

## Zero legacy tolerance rule (mandatory)

- `WordEntry` is no longer imported in `extract_words_from_text/service.py` after this task
- `_WordList.words` type changes from `list[WordEntry]` to `list[_LLMWordEntry]`
- No dead code paths. The mapping from `_LLMWordEntry` to `Word` is the new single code path.

## Acceptance criteria (testable)

1. `WordExtractor.extract()` returns `list[Word]` (not `list[WordEntry]`)
2. Each returned `Word` has `language=Language.NL` (set by service, not LLM)
3. Each returned `Word` has `word_type` as `PartOfSpeech` Enum (not string)
4. `_WordList` uses `_LLMWordEntry` internally (LLM schema without `language`)
5. Prompt generator system instruction no longer references `WordEntry`
6. `nl.json` is regenerated and reflects the updated system instruction
7. `uv run pytest tests/unit/core/ tests/unit/extract_words_from_text/ -x -v` -- all pass
8. `doppler run -- uv run pytest tests/integration/extract_words_from_text/ tests/e2e/extract_words_from_text/ -x -v` -- all pass
9. `make check` -- all pass
10. No quality regression in integration/e2e tests (same accuracy as before)

## Verification / quality gates

- [ ] `WordExtractor.extract()` return type is `list[Word]`
- [ ] Internal `_LLMWordEntry` model has `normalized_form: str` and `word_type: PartOfSpeech` (no `language`)
- [ ] `_WordList.words` type is `list[_LLMWordEntry]`
- [ ] Service maps `_LLMWordEntry` to `Word` with `language=self._language`
- [ ] System instruction in prompt generator updated (no `WordEntry` reference)
- [ ] `nl.json` regenerated
- [ ] Unit tests updated: `isinstance(w, Word)`, `w.word_type == PartOfSpeech.NOUN`, `w.language == Language.NL`
- [ ] Integration tests updated: `w.word_type.value` in set comprehensions
- [ ] E2e tests updated: `isinstance(w, Word)`, `isinstance(w.word_type, PartOfSpeech)`
- [ ] `uv run pytest tests/unit/core/ tests/unit/extract_words_from_text/ -x -v` -- all pass
- [ ] `doppler run -- uv run pytest tests/integration/extract_words_from_text/ tests/e2e/extract_words_from_text/ -x -v` -- all pass
- [ ] `make check` -- all pass

## Edge cases

- LLM returns a word_type string not in `PartOfSpeech` (e.g., `"interjection"`) -- Pydantic will reject it, `APIError` will be raised. This is correct.
- LLM returns empty `words` list -- maps to empty `list[Word]`, same as before.
- Empty input text -- LLM returns empty list, which maps to empty `list[Word]`.

## Notes / risks

- **Risk**: The LLM may occasionally return word types not in the `PartOfSpeech` Enum.
  - **Mitigation**: The prompt already lists the exact same word types that are now in the Enum. The few-shot examples demonstrate these types. If a new type appears, it will be caught by Pydantic validation and raised as `APIError` -- a clear signal to extend the Enum.

- **Risk**: Prompt regeneration might subtly change LLM behavior.
  - **Mitigation**: The only change to the prompt is replacing "WordEntry" with "woord-objecten" in the system instruction. Few-shot examples are UNCHANGED. Integration/e2e tests validate the exact same quality thresholds.
