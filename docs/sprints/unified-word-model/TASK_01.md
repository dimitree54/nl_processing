---
Task ID: T1
Title: Add PartOfSpeech Enum and Word model to core (alongside existing models)
Sprint: 2026-03-04_unified-word-model
Module: core
Depends on: --
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Add the `PartOfSpeech` Enum and unified `Word` Pydantic model to `nl_processing/core/models.py` WITHOUT removing or modifying the existing `WordEntry` and `TranslationResult` models. This establishes the new types that subsequent tasks will migrate to, while keeping the existing codebase fully functional.

## Context (contract mapping)

- Architecture: `docs/planning-artifacts/architecture.md` -- section "Core Package = Shared Models + Exceptions + Helpers Only"
- Module spec: `nl_processing/core/models.py` -- current models: `Language`, `ExtractedText`, `WordEntry`, `TranslationResult`

## Preconditions

- Current `make check` passes (codebase is green)

## Non-goals

- Do NOT remove `WordEntry` or `TranslationResult` (that is T4)
- Do NOT modify any module services or tests beyond `core`
- Do NOT modify any prompt generators or prompt JSON files

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/core/models.py` -- add new models
- `tests/unit/core/test_models.py` -- add tests for new models
- `vulture_whitelist.py` -- add `PartOfSpeech` and `Word` if flagged as unused (they will be unused until T2/T3)

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/extract_words_from_text/` (any file)
- `nl_processing/translate_word/` (any file)
- `nl_processing/translate_text/` (any file)
- `nl_processing/extract_text_from_image/` (any file)
- `nl_processing/database/` (any file)
- `nl_processing/core/exceptions.py`
- `nl_processing/core/prompts.py`
- Any test file except `tests/unit/core/test_models.py`

**Test scope:**
- Tests go in: `tests/unit/core/test_models.py`
- Test command: `uv run pytest tests/unit/core/ -x -v`

## Touched surface (expected files / modules)

- `nl_processing/core/models.py` -- add `PartOfSpeech` Enum and `Word` model
- `tests/unit/core/test_models.py` -- add tests for new models
- `vulture_whitelist.py` -- possibly whitelist `PartOfSpeech` and `Word`

## Dependencies and sequencing notes

- No dependencies. This is the first task.
- Must be completed before T2 can begin (T2 will import `Word` from core).

## Implementation steps (developer-facing)

### Step 1: Add `PartOfSpeech` Enum to `nl_processing/core/models.py`

Add the following Enum class AFTER the existing `Language` Enum and BEFORE the `ExtractedText` class. The Enum inherits from `Enum` (already imported):

```python
class PartOfSpeech(Enum):
    """Part of speech classification for extracted and translated words.

    This enum is extensible -- additional values can be added for
    language-specific grammatical categories (e.g., proper_noun_city,
    particle) without breaking existing code that doesn't use them.
    """

    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    ARTICLE = "article"
    NUMERAL = "numeral"
    PROPER_NOUN_PERSON = "proper_noun_person"
    PROPER_NOUN_COUNTRY = "proper_noun_country"
```

### Step 2: Add `Word` model to `nl_processing/core/models.py`

Add the following Pydantic model AFTER the new `PartOfSpeech` Enum. It must import `Language` (already in the file) and reference `PartOfSpeech`:

```python
class Word(BaseModel):
    """Unified word model for extracted and translated words.

    Used as the public return type for both extract_words_from_text
    and translate_word modules. The language field is set
    programmatically by the service, not by the LLM.
    """

    normalized_form: str
    word_type: PartOfSpeech
    language: Language
```

### Step 3: Verify the full file structure

After adding, the file should contain (in order):
1. `from enum import Enum`
2. `from pydantic import BaseModel`
3. `class Language(Enum)` -- UNCHANGED
4. `class PartOfSpeech(Enum)` -- NEW
5. `class ExtractedText(BaseModel)` -- UNCHANGED
6. `class Word(BaseModel)` -- NEW
7. `class WordEntry(BaseModel)` -- UNCHANGED (still present)
8. `class TranslationResult(BaseModel)` -- UNCHANGED (still present)

### Step 4: Add tests for new models in `tests/unit/core/test_models.py`

Add the following imports at the top of the test file (add `PartOfSpeech` and `Word` to the existing import from `nl_processing.core.models`):

```python
from nl_processing.core.models import ExtractedText, Language, PartOfSpeech, TranslationResult, Word, WordEntry
```

Add the following test functions AFTER the existing tests (before `test_all_models_accept_empty_strings`):

```python
def test_part_of_speech_enum_values() -> None:
    """Test PartOfSpeech enum has correct values."""
    assert PartOfSpeech.NOUN.value == "noun"
    assert PartOfSpeech.VERB.value == "verb"
    assert PartOfSpeech.ADJECTIVE.value == "adjective"
    assert PartOfSpeech.ADVERB.value == "adverb"
    assert PartOfSpeech.PREPOSITION.value == "preposition"
    assert PartOfSpeech.CONJUNCTION.value == "conjunction"
    assert PartOfSpeech.PRONOUN.value == "pronoun"
    assert PartOfSpeech.ARTICLE.value == "article"
    assert PartOfSpeech.NUMERAL.value == "numeral"
    assert PartOfSpeech.PROPER_NOUN_PERSON.value == "proper_noun_person"
    assert PartOfSpeech.PROPER_NOUN_COUNTRY.value == "proper_noun_country"


def test_part_of_speech_enum_count() -> None:
    """Test PartOfSpeech enum has exactly 11 members."""
    assert len(list(PartOfSpeech)) == 11


def test_part_of_speech_enum_invalid_value() -> None:
    """Test PartOfSpeech enum rejects invalid values."""
    with pytest.raises(ValueError):
        PartOfSpeech("invalid")


def test_part_of_speech_from_string() -> None:
    """Test PartOfSpeech can be created from string value."""
    assert PartOfSpeech("noun") == PartOfSpeech.NOUN
    assert PartOfSpeech("proper_noun_person") == PartOfSpeech.PROPER_NOUN_PERSON


def test_word_instantiation() -> None:
    """Test Word can be created and accessed."""
    word = Word(normalized_form="de fiets", word_type=PartOfSpeech.NOUN, language=Language.NL)
    assert word.normalized_form == "de fiets"
    assert word.word_type == PartOfSpeech.NOUN
    assert word.language == Language.NL


def test_word_with_string_word_type() -> None:
    """Test Word accepts string value for word_type (Pydantic coercion)."""
    word = Word(normalized_form="lopen", word_type="verb", language=Language.NL)
    assert word.word_type == PartOfSpeech.VERB


def test_word_serialization() -> None:
    """Test Word serialization via model_dump."""
    word = Word(normalized_form="de kat", word_type=PartOfSpeech.NOUN, language=Language.NL)
    data = word.model_dump()
    assert data == {"normalized_form": "de kat", "word_type": "noun", "language": "nl"}


def test_word_missing_fields() -> None:
    """Test Word raises ValidationError on missing fields."""
    with pytest.raises(ValidationError):
        Word(normalized_form="de fiets", word_type=PartOfSpeech.NOUN)

    with pytest.raises(ValidationError):
        Word(normalized_form="de fiets", language=Language.NL)

    with pytest.raises(ValidationError):
        Word(word_type=PartOfSpeech.NOUN, language=Language.NL)

    with pytest.raises(ValidationError):
        Word()


def test_word_invalid_word_type() -> None:
    """Test Word rejects invalid word_type values."""
    with pytest.raises(ValidationError):
        Word(normalized_form="test", word_type="invalid_type", language=Language.NL)


def test_word_russian_language() -> None:
    """Test Word with Russian language (for translate_word output)."""
    word = Word(normalized_form="дом", word_type=PartOfSpeech.NOUN, language=Language.RU)
    assert word.normalized_form == "дом"
    assert word.word_type == PartOfSpeech.NOUN
    assert word.language == Language.RU
```

### Step 5: Update `test_all_models_accept_empty_strings`

The existing `test_all_models_accept_empty_strings` test creates a `WordEntry(normalized_form="", word_type="")`. This test is about the OLD models and should remain unchanged. Do NOT modify it.

### Step 6: Handle vulture whitelist

Run `uv run vulture nl_processing tests vulture_whitelist.py` to check if `PartOfSpeech` or `Word` are flagged as unused. If they are, add them to `vulture_whitelist.py`:

```python
from nl_processing.core.models import PartOfSpeech, Word
```

And add to the `__all__` list:

```python
"PartOfSpeech",
"Word",
```

### Step 7: Run verification

```bash
uv run pytest tests/unit/core/ -x -v
```

All tests must pass, including both old tests (for `WordEntry`, `TranslationResult`) and new tests (for `PartOfSpeech`, `Word`).

Then run the full check to make sure nothing else broke:

```bash
make check
```

## Production safety constraints (mandatory)

- **Database operations**: None. This task only adds Python model classes.
- **Resource isolation**: N/A. No shared resources affected.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using existing `Enum` import and `BaseModel` import already in the file.
- **Correct libraries only**: `pydantic.BaseModel` (already in `pyproject.toml` via `langchain` dependency), `enum.Enum` (stdlib).
- **Correct file locations**: Adding to existing `nl_processing/core/models.py` -- no new files.
- **No regressions**: Existing tests for `WordEntry`, `TranslationResult`, `Language`, `ExtractedText` must all still pass. No modifications to existing code.

## Error handling + correctness rules (mandatory)

- No error handling changes in this task. Models are data classes only.
- Pydantic validation will automatically reject invalid `PartOfSpeech` values -- this is correct behavior (fail fast).

## Zero legacy tolerance rule (mandatory)

- This task explicitly does NOT remove old models (that is T4). The coexistence is intentional and temporary.
- No dead code is introduced -- the new models will be consumed starting in T2.
- The vulture whitelist entry (if needed) documents the intentional temporary unused state.

## Acceptance criteria (testable)

1. `PartOfSpeech` Enum exists in `nl_processing/core/models.py` with exactly 11 values: `NOUN`, `VERB`, `ADJECTIVE`, `ADVERB`, `PREPOSITION`, `CONJUNCTION`, `PRONOUN`, `ARTICLE`, `NUMERAL`, `PROPER_NOUN_PERSON`, `PROPER_NOUN_COUNTRY`
2. `Word` model exists in `nl_processing/core/models.py` with fields `normalized_form: str`, `word_type: PartOfSpeech`, `language: Language`
3. `WordEntry` and `TranslationResult` still exist and are unchanged
4. `from nl_processing.core.models import PartOfSpeech, Word` works
5. `Word(normalized_form="de fiets", word_type=PartOfSpeech.NOUN, language=Language.NL)` creates a valid instance
6. `Word(normalized_form="de fiets", word_type="noun", language=Language.NL)` creates a valid instance (Pydantic string-to-enum coercion)
7. `Word(normalized_form="test", word_type="invalid", language=Language.NL)` raises `ValidationError`
8. `uv run pytest tests/unit/core/ -x -v` passes 100%
9. `make check` passes 100% green

## Verification / quality gates

- [ ] `PartOfSpeech` Enum has exactly 11 members with correct string values
- [ ] `Word` model has all 3 required fields with correct types
- [ ] Existing `WordEntry` and `TranslationResult` tests still pass (no regressions)
- [ ] New tests for `PartOfSpeech` cover: values, count, invalid value, string construction
- [ ] New tests for `Word` cover: instantiation, string coercion, serialization, missing fields, invalid word_type, Russian language
- [ ] `uv run pytest tests/unit/core/ -x -v` -- all pass
- [ ] `make check` -- all pass
- [ ] Vulture whitelist updated if needed (no false-positive "unused" warnings)

## Edge cases

- `Word` with empty `normalized_form=""` should be valid (consistent with existing `WordEntry` behavior where empty strings are accepted)
- `PartOfSpeech("noun")` must work (string-to-enum construction) -- verified by test
- `Word.model_dump()` must serialize `word_type` as string `"noun"` not `PartOfSpeech.NOUN` -- verified by serialization test

## Notes / risks

- **Risk**: Vulture may flag `PartOfSpeech` and `Word` as unused since no module imports them yet.
  - **Mitigation**: Add to `vulture_whitelist.py` with comment explaining they're used starting in T2. Remove whitelist entries in T4 when old models are removed.
