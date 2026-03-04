---
Task ID: T3
Title: Migrate translate_word to use Word model (input and output)
Sprint: 2026-03-04_unified-word-model
Module: translate_word
Depends on: T2
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Migrate the `translate_word` module to use the unified `Word` model. Change the input from `list[str]` to `list[Word]` and the output from `list[TranslationResult]` to `list[Word]`. The LLM now returns `{normalized_form, word_type}` for each translated word (determining POS itself for the target language). Update the prompt generator with new few-shot examples. Regenerate the prompt JSON. Update all tests (unit, integration, e2e). After this task, `TranslationResult` is no longer imported anywhere in this module.

## Context (contract mapping)

- Architecture: `nl_processing/translate_word/docs/architecture_translate_word.md` -- "TranslationResult -- Minimal Pydantic Model" decision (being replaced)
- PRD: `nl_processing/translate_word/docs/prd_translate_word.md` -- FR2: "list of TranslationResult objects" (changing to `list[Word]`)
- Current service: `nl_processing/translate_word/service.py` -- `translate(words: list[str]) -> list[TranslationResult]`
- Current prompt: `nl_processing/translate_word/prompts/generate_nl_ru_prompt.py` -- few-shot examples with `{"translation": "..."}` format

## Preconditions

- T1 completed: `PartOfSpeech` Enum and `Word` model exist in `core/models.py`
- T2 completed: `extract_words_from_text` returns `list[Word]`

## Non-goals

- Do NOT remove `TranslationResult` from `core/models.py` (that is T4)
- Do NOT touch `extract_words_from_text` module (done in T2)
- Do NOT touch `translate_text` or `extract_text_from_image`
- Do NOT change the one-to-one order-preserving mapping contract

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/translate_word/service.py`
- `nl_processing/translate_word/prompts/generate_nl_ru_prompt.py`
- `nl_processing/translate_word/prompts/nl_ru.json` (regenerated)
- `tests/unit/translate_word/test_word_translator.py`
- `tests/unit/translate_word/conftest.py`
- `tests/unit/translate_word/test_error_handling.py`
- `tests/integration/translate_word/test_translation_accuracy.py`
- `tests/e2e/translate_word/test_full_translation.py`
- `tests/e2e/translate_word/test_product_box_quality.py`

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/models.py`
- `nl_processing/extract_words_from_text/` (any file)
- `nl_processing/translate_text/` (any file)
- `nl_processing/extract_text_from_image/` (any file)
- `nl_processing/database/` (any file)
- Any test files not listed above
- `vulture_whitelist.py`

**Test scope:**
- Unit: `uv run pytest tests/unit/core/ tests/unit/translate_word/ -x -v`
- Integration + e2e: `doppler run -- uv run pytest tests/integration/translate_word/ tests/e2e/translate_word/ -x -v`

## Touched surface (expected files / modules)

- `nl_processing/translate_word/service.py` -- change input/output types, update internal model
- `nl_processing/translate_word/prompts/generate_nl_ru_prompt.py` -- new few-shot format
- `nl_processing/translate_word/prompts/nl_ru.json` -- regenerated artifact
- `tests/unit/translate_word/test_word_translator.py` -- major rewrite
- `tests/unit/translate_word/conftest.py` -- update mock response format
- `tests/unit/translate_word/test_error_handling.py` -- update input format
- `tests/integration/translate_word/test_translation_accuracy.py` -- major rewrite
- `tests/e2e/translate_word/test_full_translation.py` -- major rewrite
- `tests/e2e/translate_word/test_product_box_quality.py` -- update to use `Word` input

## Dependencies and sequencing notes

- Depends on T2: needs `extract_words_from_text` using `Word` model so the pipeline is consistent
- Must be completed before T4: need both modules migrated before removing old models

## Implementation steps (developer-facing)

### Step 1: Update `nl_processing/translate_word/service.py`

#### 1a. Change imports

Replace:
```python
from nl_processing.core.models import Language, TranslationResult
```
With:
```python
from nl_processing.core.models import Language, PartOfSpeech, Word
```

#### 1b. Replace `_TranslationBatch` internal model

The current internal model:
```python
class _TranslationBatch(BaseModel):
    translations: list[TranslationResult]
```

Replace with an internal LLM-facing model:

```python
class _LLMTranslationEntry(BaseModel):
    """Single translated word as returned by the LLM (no language field)."""
    normalized_form: str
    word_type: PartOfSpeech


class _TranslationBatch(BaseModel):
    """Internal wrapper: bind_tools needs a single model."""
    translations: list[_LLMTranslationEntry]
```

**Why `_LLMTranslationEntry`?** Same rationale as T2: the LLM returns `{normalized_form, word_type}` and the service adds `language=self._target_language` programmatically. The LLM now determines both the translated form AND the part of speech for the target language.

#### 1c. Update `translate()` method signature and body

Change the method signature from:
```python
async def translate(self, words: list[str]) -> list[TranslationResult]:
```
To:
```python
async def translate(self, words: list[Word]) -> list[Word]:
```

Update the method body:

```python
async def translate(self, words: list[Word]) -> list[Word]:
    """Translate a list of Word objects from source to target language.

    Returns one Word per input word (in target language), in the same order.
    Returns empty list for empty input (no API call).
    """
    if not words:
        return []

    word_text = "\n".join(w.normalized_form for w in words)

    try:
        response = await self._chain.ainvoke({"text": [HumanMessage(content=word_text)]})
        result = _TranslationBatch(
            **response.tool_calls[0]["args"]  # type: ignore[attr-defined]
        )
    except Exception as e:
        raise APIError(str(e)) from e

    return [
        Word(
            normalized_form=entry.normalized_form,
            word_type=entry.word_type,
            language=self._target_language,
        )
        for entry in result.translations
    ]
```

Key changes:
- Input is `list[Word]` -- we extract `.normalized_form` to build the LLM input text
- Output maps `_LLMTranslationEntry` to `Word` with `language=self._target_language`
- The `word_text` construction changes from `"\n".join(words)` to `"\n".join(w.normalized_form for w in words)`

### Step 2: Update `nl_processing/translate_word/prompts/generate_nl_ru_prompt.py`

This is a major change. The few-shot examples must change from `{"translation": "..."}` format to `{"normalized_form": "...", "word_type": "..."}` format.

#### 2a. Update `SYSTEM_INSTRUCTION`

Replace the current `SYSTEM_INSTRUCTION` with:

```python
SYSTEM_INSTRUCTION = (
    "Вы — профессиональный переводчик с нидерландского языка на русский. "
    "Вы получаете список нидерландских слов или фраз и должны перевести каждое на русский. "
    "Верните ровно один перевод для каждого входного слова, в том же порядке. "
    "Количество переводов в результате должно равняться количеству слов на входе. "
    "Каждый перевод должен содержать нормализованную форму слова на русском языке "
    "и часть речи (word_type). "
    "Возможные значения word_type: noun, verb, adjective, adverb, preposition, "
    "conjunction, pronoun, article, numeral, proper_noun_person, proper_noun_country. "
    "Если входной список пуст, верните пустой список."
)
```

Key additions: the LLM is now instructed to return `normalized_form` and `word_type` for each translated word, and told the allowed `word_type` values.

#### 2b. Update few-shot examples

Replace the current example constants with:

```python
EXAMPLE_1_INPUT = "huis\nlopen\nsnel"
EXAMPLE_1_OUTPUT = [
    {"normalized_form": "дом", "word_type": "noun"},
    {"normalized_form": "ходить", "word_type": "verb"},
    {"normalized_form": "быстро", "word_type": "adverb"},
]

EXAMPLE_2_INPUT = "de kat\nhet boek\nschrijven\nmooi\nin"
EXAMPLE_2_OUTPUT = [
    {"normalized_form": "кошка", "word_type": "noun"},
    {"normalized_form": "книга", "word_type": "noun"},
    {"normalized_form": "писать", "word_type": "verb"},
    {"normalized_form": "красивый", "word_type": "adjective"},
    {"normalized_form": "в", "word_type": "preposition"},
]

EXAMPLE_3_INPUT = "er vandoor gaan\nde fiets"
EXAMPLE_3_OUTPUT = [
    {"normalized_form": "сбежать", "word_type": "verb"},
    {"normalized_form": "велосипед", "word_type": "noun"},
]

EXAMPLE_4_INPUT = ""
EXAMPLE_4_OUTPUT: list[dict[str, str]] = []
```

#### 2c. Update `_make_example_ai` function

The tool name must match the new `_TranslationBatch` schema. The current code already uses `"_TranslationBatch"` -- keep it. But the field name inside must stay `"translations"` to match the `_TranslationBatch` wrapper.

No change needed to `_make_example_ai` -- it already produces `{"name": "_TranslationBatch", "args": {"translations": ...}}` which matches the updated `_TranslationBatch` model.

#### 2d. No structural changes to `build_prompt()`

The `build_prompt()` function structure is unchanged -- same 4 examples with same message pattern. Only the content of the examples changed (Step 2b).

### Step 3: Regenerate `nl_ru.json`

Run the prompt generator:

```bash
uv run python nl_processing/translate_word/prompts/generate_nl_ru_prompt.py
```

This regenerates `nl_processing/translate_word/prompts/nl_ru.json` with the new system instruction and few-shot examples.

### Step 4: Update unit tests

#### 4a. Update `tests/unit/translate_word/conftest.py`

The `make_tool_response` function creates mock responses. Update it to match the new response format:

The current function:
```python
def make_tool_response(translations: list[dict[str, str]]) -> object:
    """Build a fake LLM response with tool_calls for _TranslationBatch."""
    return _make_response({"translations": translations})
```

No structural change needed -- the wrapper key is still `"translations"`. The dict format inside changes from `{"translation": "..."}` to `{"normalized_form": "...", "word_type": "..."}`, but that's controlled by the test call sites, not by `conftest.py`.

#### 4b. Update `tests/unit/translate_word/test_word_translator.py`

**Change import:**
Replace:
```python
from nl_processing.core.models import Language, TranslationResult
```
With:
```python
from nl_processing.core.models import Language, PartOfSpeech, Word
```

**Update `test_translate_happy_path`:**

Replace the mock data:
```python
mock_translations = [
    {"translation": "дом"},
    {"translation": "ходить"},
    {"translation": "быстро"},
]
```
With:
```python
mock_translations = [
    {"normalized_form": "дом", "word_type": "noun"},
    {"normalized_form": "ходить", "word_type": "verb"},
    {"normalized_form": "быстро", "word_type": "adverb"},
]
```

Change the input from:
```python
results = await translator.translate(["huis", "lopen", "snel"])
```
To:
```python
input_words = [
    Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
    Word(normalized_form="snel", word_type=PartOfSpeech.ADVERB, language=Language.NL),
]
results = await translator.translate(input_words)
```

Change assertions from:
```python
assert results[0].translation == "дом"
assert results[1].translation == "ходить"
assert results[2].translation == "быстро"
```
To:
```python
assert results[0].normalized_form == "дом"
assert results[0].word_type == PartOfSpeech.NOUN
assert results[0].language == Language.RU
assert results[1].normalized_form == "ходить"
assert results[1].word_type == PartOfSpeech.VERB
assert results[1].language == Language.RU
assert results[2].normalized_form == "быстро"
assert results[2].word_type == PartOfSpeech.ADVERB
assert results[2].language == Language.RU
```

**Update `test_translate_one_to_one_mapping`:**

Replace mock data format from `{"translation": "..."}` to `{"normalized_form": "...", "word_type": "..."}`:
```python
mock_translations = [
    {"normalized_form": "дом", "word_type": "noun"},
    {"normalized_form": "книга", "word_type": "noun"},
    {"normalized_form": "вода", "word_type": "noun"},
    {"normalized_form": "солнце", "word_type": "noun"},
    {"normalized_form": "хлеб", "word_type": "noun"},
]
```

Change input from:
```python
words = ["huis", "boek", "water", "zon", "brood"]
```
To:
```python
words = [
    Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="zon", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="brood", word_type=PartOfSpeech.NOUN, language=Language.NL),
]
```

**Update `test_translate_empty_input`:**

Change input from `await translator.translate([])` -- no change needed (empty list is still valid for `list[Word]`).

Change mock from `make_tool_response([])` -- no change needed (empty list).

**Update `test_translate_preserves_order`:**

Replace mock data format. Change input to `list[Word]`. Change assertions from `results[0].translation` to `results[0].normalized_form`.

```python
mock_translations = [
    {"normalized_form": "кошка", "word_type": "noun"},
    {"normalized_form": "книга", "word_type": "noun"},
]
```

Input:
```python
input_words = [
    Word(normalized_form="de kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="het boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
]
results = await translator.translate(input_words)
```

Assertions:
```python
assert results[0].normalized_form == "кошка"
assert results[1].normalized_form == "книга"
```

**Update `test_translate_returns_translation_result_objects`:**

Rename to `test_translate_returns_word_objects`.

Replace mock data format. Change input to `list[Word]`. Change assertions:

```python
mock_translations = [{"normalized_form": "дом", "word_type": "noun"}]
translator._chain = _AsyncChainMock(make_tool_response(mock_translations))

input_words = [Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)]
results = await translator.translate(input_words)

assert len(results) == 1
assert isinstance(results[0], Word)
assert results[0].normalized_form == "дом"
assert results[0].word_type == PartOfSpeech.NOUN
assert results[0].language == Language.RU
```

#### 4c. Update `tests/unit/translate_word/test_error_handling.py`

Change input from `await translator.translate(["huis"])` and `await translator.translate(["boek"])` to use `list[Word]`:

Add import:
```python
from nl_processing.core.models import Language, PartOfSpeech, Word
```
(Replace the existing `from nl_processing.core.models import Language`)

At each `translator.translate(...)` call, replace `["huis"]` with:
```python
[Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)]
```

And `["boek"]` with:
```python
[Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL)]
```

### Step 5: Update integration tests

#### `tests/integration/translate_word/test_translation_accuracy.py`

**Change import:**
Replace:
```python
from nl_processing.core.models import Language, TranslationResult
```
With:
```python
from nl_processing.core.models import Language, PartOfSpeech, Word
```

**Update `_QUALITY_TEST_CASES`:**

The current format is `("huis", "дом")`. We need to provide `Word` objects as input and check `normalized_form` in output. Change to:

```python
_QUALITY_TEST_CASES: list[tuple[Word, str]] = [
    (Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL), "дом"),
    (Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL), "книга"),
    (Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL), "вода"),
    (Word(normalized_form="zon", word_type=PartOfSpeech.NOUN, language=Language.NL), "солнце"),
    (Word(normalized_form="brood", word_type=PartOfSpeech.NOUN, language=Language.NL), "хлеб"),
    (Word(normalized_form="melk", word_type=PartOfSpeech.NOUN, language=Language.NL), "молоко"),
    (Word(normalized_form="school", word_type=PartOfSpeech.NOUN, language=Language.NL), "школа"),
    (Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL), "стол"),
    (Word(normalized_form="stoel", word_type=PartOfSpeech.NOUN, language=Language.NL), "стул"),
    (Word(normalized_form="deur", word_type=PartOfSpeech.NOUN, language=Language.NL), "дверь"),
]
```

**Update `test_translation_quality_10_words`:**

Change:
```python
words = [word for word, _ in _QUALITY_TEST_CASES]
expected = [translation for _, translation in _QUALITY_TEST_CASES]
```
(This still works -- `word` is now a `Word` object, `translation` is a string.)

Change assertion from `result.translation` to `result.normalized_form`:
```python
assert result.normalized_form == expected_translation, (
    f"Word #{i} '{words[i].normalized_form}': expected '{expected_translation}', got '{result.normalized_form}'"
)
```

**Update `test_one_to_one_mapping_5_words`:**

Change input:
```python
words = [
    Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="zon", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="brood", word_type=PartOfSpeech.NOUN, language=Language.NL),
]
```

Change type checks from `isinstance(result, TranslationResult)` to `isinstance(result, Word)`.
Change `result.translation.strip()` to `result.normalized_form.strip()`.

**Update `test_translation_performance_10_words`:**

Change input to use `Word` objects (same pattern as above).

**Update `test_empty_input_returns_empty_list`:**

No changes needed -- empty list is still valid.

### Step 6: Update e2e tests

#### `tests/e2e/translate_word/test_full_translation.py`

**Change import:**
Replace:
```python
from nl_processing.core.models import Language, TranslationResult
```
With:
```python
from nl_processing.core.models import Language, PartOfSpeech, Word
```

**Update `test_realistic_pipeline_input`:**

Change input from string list to `list[Word]`:
```python
words = [
    Word(normalized_form="de kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
    Word(normalized_form="mooi", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
    Word(normalized_form="in", word_type=PartOfSpeech.PREPOSITION, language=Language.NL),
    Word(normalized_form="Nederland", word_type=PartOfSpeech.PROPER_NOUN_COUNTRY, language=Language.NL),
]
```

Change type checks from `isinstance(result, TranslationResult)` to `isinstance(result, Word)`.
Change `result.translation.strip()` to `result.normalized_form.strip()`.
Update error messages to reference `Word` instead of `TranslationResult`.

**Update `test_one_to_one_mapping_verification`:**

Change input to `list[Word]`:
```python
words = [
    Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
]
```

Change type checks and attribute accesses same as above.

**Update `test_empty_input_handling`:**

No changes needed.

**Update `test_unsupported_pair_at_init`:**

No changes needed (tests constructor, not translate method).

**Update `test_single_word_translation`:**

Change input to `list[Word]`:
```python
input_words = [Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)]
results = await translator.translate(input_words)
```

Change type check and assertion:
```python
assert isinstance(results[0], Word)
assert results[0].normalized_form.strip(), "Translation should not be empty"
assert results[0].language == Language.RU
```

#### `tests/e2e/translate_word/test_product_box_quality.py`

**Change import:**

Add `PartOfSpeech, Word` to the import:
```python
from nl_processing.core.models import Language, PartOfSpeech, Word
```

**Update `PRODUCT_BOX_WORDS`:**

Change the type from `list[tuple[str, set[str]]]` to `list[tuple[Word, set[str]]]`:

```python
PRODUCT_BOX_WORDS: list[tuple[Word, set[str]]] = [
    (Word(normalized_form="kunnen", word_type=PartOfSpeech.VERB, language=Language.NL), {"мочь", "уметь"}),
    (Word(normalized_form="genieten", word_type=PartOfSpeech.VERB, language=Language.NL), {"наслаждаться", "получать удовольствие"}),
    (Word(normalized_form="elk", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"каждый", "каждая", "каждое", "всякий"}),
    (Word(normalized_form="de dag", word_type=PartOfSpeech.NOUN, language=Language.NL), {"день"}),
    (Word(normalized_form="breed", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"широкий"}),
    (Word(normalized_form="het assortiment", word_type=PartOfSpeech.NOUN, language=Language.NL), {"ассортимент"}),
    (Word(normalized_form="smakelijk", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"вкусный"}),
    (Word(normalized_form="het product", word_type=PartOfSpeech.NOUN, language=Language.NL), {"продукт", "товар"}),
    (Word(normalized_form="de chocoladevlokken", word_type=PartOfSpeech.NOUN, language=Language.NL), {"шоколадные хлопья", "шоколадная стружка"}),
    (Word(normalized_form="de melk", word_type=PartOfSpeech.NOUN, language=Language.NL), {"молоко"}),
    (Word(normalized_form="puur", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"чистый", "горький", "тёмный", "темный"}),
    (Word(normalized_form="de chocoladehagel", word_type=PartOfSpeech.NOUN, language=Language.NL), {"шоколадная посыпка", "шоколадная крошка"}),
    (Word(normalized_form="de vruchtenhagel", word_type=PartOfSpeech.NOUN, language=Language.NL), {"фруктовая посыпка", "фруктовая крошка"}),
    (Word(normalized_form="de anijshagel", word_type=PartOfSpeech.NOUN, language=Language.NL), {"анисовая посыпка", "анисовая крошка"}),
    (Word(normalized_form="roze", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"розовый", "розовая", "розовое"}),
    (Word(normalized_form="wit", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"белый", "белая", "белое"}),
    (Word(normalized_form="blauw", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"голубой", "синий", "голубая", "синяя"}),
    (Word(normalized_form="De Ruijter", word_type=PartOfSpeech.PROPER_NOUN_PERSON, language=Language.NL), {"Де Рёйтер", "Де Рюйтер", "Де Рейтер", "De Ruijter"}),
]
```

**Update `test_product_box_translation_quality`:**

Change input construction from:
```python
words = [w for w, _ in PRODUCT_BOX_WORDS]
```
(Still works -- `w` is now a `Word` object.)

Change assertion from `results[i].translation` to `results[i].normalized_form`:
```python
actual = results[i].normalized_form
```

Update error message to use `dutch.normalized_form` instead of `dutch`:
```python
failures.append(f"  [{dutch.normalized_form!r}] -> got {actual!r}, expected one of {sorted(acceptable)}")
```

### Step 7: Run all verification commands

```bash
# Unit tests (core + translate_word)
uv run pytest tests/unit/core/ tests/unit/translate_word/ -x -v

# Integration + e2e tests (requires API keys via Doppler)
doppler run -- uv run pytest tests/integration/translate_word/ tests/e2e/translate_word/ -x -v
```

**CRITICAL**: If integration or e2e tests fail due to LLM quality regression (the new prompt format causes different translations), STOP and report to user. Do NOT loosen quality gates. Do NOT relax assertion thresholds. Do NOT add new acceptable translations to the product box test.

Then run the full check:

```bash
make check
```

## Production safety constraints (mandatory)

- **Database operations**: None. This task changes Python code only.
- **Resource isolation**: Integration/e2e tests make OpenAI API calls. Uses development Doppler environment.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reusing `PartOfSpeech` and `Word` from core (T1). Following the same `_LLM*Entry` pattern established in T2.
- **Correct libraries only**: No new libraries.
- **Correct file locations**: All changes in existing files. No new files.
- **No regressions**: All existing quality thresholds must be maintained. The prompt change is significant (new output format) so integration/e2e tests are critical.

## Error handling + correctness rules (mandatory)

- The `APIError` wrapping in `translate()` is unchanged.
- Pydantic validation in `_LLMTranslationEntry` will reject invalid `word_type` values -- correct behavior.
- If the LLM returns a `word_type` not in `PartOfSpeech`, it surfaces as `APIError`.

## Zero legacy tolerance rule (mandatory)

- `TranslationResult` is no longer imported in `translate_word/service.py`
- `_TranslationBatch.translations` type changes from `list[TranslationResult]` to `list[_LLMTranslationEntry]`
- All test files no longer reference `TranslationResult`
- No dead code paths

## Acceptance criteria (testable)

1. `WordTranslator.translate()` accepts `list[Word]` input (not `list[str]`)
2. `WordTranslator.translate()` returns `list[Word]` (not `list[TranslationResult]`)
3. Each returned `Word` has `language=Language.RU` (set by service)
4. Each returned `Word` has `word_type` as `PartOfSpeech` Enum
5. Each returned `Word` has `normalized_form` with the Russian translation
6. `_TranslationBatch` uses `_LLMTranslationEntry` internally
7. Prompt generator has new system instruction mentioning `normalized_form` and `word_type`
8. Prompt generator few-shot examples use `{"normalized_form": "...", "word_type": "..."}` format
9. `nl_ru.json` is regenerated
10. `uv run pytest tests/unit/core/ tests/unit/translate_word/ -x -v` -- all pass
11. `doppler run -- uv run pytest tests/integration/translate_word/ tests/e2e/translate_word/ -x -v` -- all pass
12. `make check` -- all pass
13. No quality regression in integration/e2e tests

## Verification / quality gates

- [ ] `WordTranslator.translate()` input type is `list[Word]`
- [ ] `WordTranslator.translate()` return type is `list[Word]`
- [ ] Internal `_LLMTranslationEntry` has `normalized_form: str` and `word_type: PartOfSpeech`
- [ ] `_TranslationBatch.translations` type is `list[_LLMTranslationEntry]`
- [ ] Service maps entries to `Word` with `language=self._target_language`
- [ ] System instruction updated with `normalized_form`, `word_type`, and allowed values
- [ ] Few-shot examples use new format
- [ ] `nl_ru.json` regenerated
- [ ] All unit tests pass with `Word` input/output
- [ ] All integration tests pass (exact match on 10 words)
- [ ] All e2e tests pass (product box quality, pipeline input, etc.)
- [ ] `uv run pytest tests/unit/core/ tests/unit/translate_word/ -x -v` -- all pass
- [ ] `doppler run -- uv run pytest tests/integration/translate_word/ tests/e2e/translate_word/ -x -v` -- all pass
- [ ] `make check` -- all pass

## Edge cases

- Empty `list[Word]` input -- returns empty `list[Word]` (no API call, same as before)
- LLM returns a `word_type` not in `PartOfSpeech` -- Pydantic rejects, `APIError` raised
- LLM returns wrong number of translations -- one-to-one contract is enforced by prompt, but Pydantic accepts any list length. If `len(output) != len(input)`, downstream callers will notice. This behavior is unchanged from before.
- `Word` input with `language != Language.NL` -- the service extracts `.normalized_form` regardless of language. The source language validation is at the constructor level (supported pairs check), not per-word.

## Notes / risks

- **Risk**: The new prompt format (`{normalized_form, word_type}` instead of `{translation}`) significantly changes what the LLM produces. This could affect translation quality.
  - **Mitigation**: The system instruction explicitly lists allowed `word_type` values. Few-shot examples demonstrate the format clearly. Integration tests with 100% exact match threshold are the quality gate. If they fail, STOP and report.

- **Risk**: The product box quality test has specific acceptable translation sets. The new format might cause the LLM to produce slightly different translations.
  - **Mitigation**: The acceptable sets already include multiple valid alternatives. If the LLM produces a valid translation not in the set, report to user -- they decide whether to add it.
