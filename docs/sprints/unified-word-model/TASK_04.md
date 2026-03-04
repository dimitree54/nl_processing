---
Task ID: T4
Title: Remove deprecated WordEntry and TranslationResult from core
Sprint: 2026-03-04_unified-word-model
Module: core
Depends on: T3
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Remove the now-unused `WordEntry` and `TranslationResult` models from `nl_processing/core/models.py`. Update core tests to remove old model tests. Clean up vulture whitelist if needed. After this task, the only public models in `core/models.py` are: `Language`, `PartOfSpeech`, `ExtractedText`, and `Word`.

## Context (contract mapping)

- Architecture: `docs/planning-artifacts/architecture.md` -- section "Core Package = Shared Models + Exceptions + Helpers Only", mentions `WordEntry` and `TranslationResult`
- Current state: After T2 and T3, no module imports `WordEntry` or `TranslationResult` anymore

## Preconditions

- T1 completed: `PartOfSpeech` and `Word` exist in `core/models.py`
- T2 completed: `extract_words_from_text` uses `Word`, not `WordEntry`
- T3 completed: `translate_word` uses `Word`, not `TranslationResult`
- No module in the project imports `WordEntry` or `TranslationResult`

## Non-goals

- Do NOT modify any module services (already migrated in T2/T3)
- Do NOT modify any module tests (already updated in T2/T3)
- Do NOT update documentation (that is T5)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/core/models.py` -- remove `WordEntry` and `TranslationResult`
- `tests/unit/core/test_models.py` -- remove tests for old models, update remaining tests
- `vulture_whitelist.py` -- clean up entries if needed

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/extract_words_from_text/` (any file)
- `nl_processing/translate_word/` (any file)
- `nl_processing/translate_text/` (any file)
- `nl_processing/extract_text_from_image/` (any file)
- `nl_processing/database/` (any file)
- `nl_processing/core/exceptions.py`
- `nl_processing/core/prompts.py`
- Any test file except `tests/unit/core/test_models.py`
- Any documentation files

**Test scope:**
- Tests go in: `tests/unit/core/test_models.py`
- Test command: `uv run pytest tests/unit/core/ -x -v`

## Touched surface (expected files / modules)

- `nl_processing/core/models.py` -- remove 2 classes
- `tests/unit/core/test_models.py` -- remove tests for old classes, update imports
- `vulture_whitelist.py` -- possibly remove `PartOfSpeech`/`Word` whitelist entries from T1

## Dependencies and sequencing notes

- Depends on T3: all modules must be migrated before removing old models
- Must be completed before T5: documentation update should reflect the final model state

## Implementation steps (developer-facing)

### Step 1: Verify no remaining imports of `WordEntry` or `TranslationResult`

Before removing, verify that no code outside `core` imports these models. Run:

```bash
uv run rg "WordEntry" --type py nl_processing/ tests/
uv run rg "TranslationResult" --type py nl_processing/ tests/
```

Expected results:
- `WordEntry` should only appear in `nl_processing/core/models.py` and `tests/unit/core/test_models.py`
- `TranslationResult` should only appear in `nl_processing/core/models.py` and `tests/unit/core/test_models.py`

If any other files reference these models, STOP -- those files were not updated in T2/T3 and need investigation.

### Step 2: Remove `WordEntry` from `nl_processing/core/models.py`

Delete the entire `WordEntry` class (lines 15-17 in the current file):

```python
class WordEntry(BaseModel):
    normalized_form: str
    word_type: str
```

Remove the blank line after it as well.

### Step 3: Remove `TranslationResult` from `nl_processing/core/models.py`

Delete the entire `TranslationResult` class (lines 20-21 in the current file):

```python
class TranslationResult(BaseModel):
    translation: str
```

### Step 4: Verify final `models.py` structure

After removal, the file should contain (in order):
1. `from enum import Enum`
2. `from pydantic import BaseModel`
3. `class Language(Enum)` -- NL, RU
4. `class PartOfSpeech(Enum)` -- 11 members
5. `class ExtractedText(BaseModel)` -- text field
6. `class Word(BaseModel)` -- normalized_form, word_type, language

That's it. No `WordEntry`. No `TranslationResult`.

### Step 5: Update `tests/unit/core/test_models.py`

#### 5a. Update imports

Replace:
```python
from nl_processing.core.models import ExtractedText, Language, PartOfSpeech, TranslationResult, Word, WordEntry
```
With:
```python
from nl_processing.core.models import ExtractedText, Language, PartOfSpeech, Word
```

(Remove `TranslationResult` and `WordEntry` from the import.)

#### 5b. Remove old model tests

Delete the following test functions entirely:

- `test_word_entry_instantiation` -- tests `WordEntry` which no longer exists
- `test_word_entry_missing_fields` -- tests `WordEntry` which no longer exists
- `test_translation_result_instantiation` -- tests `TranslationResult` which no longer exists
- `test_translation_result_missing_field` -- tests `TranslationResult` which no longer exists

#### 5c. Update `test_all_models_accept_empty_strings`

This test currently creates instances of `ExtractedText`, `WordEntry`, and `TranslationResult`. Replace it:

Current:
```python
def test_all_models_accept_empty_strings() -> None:
    """Test all models accept empty strings (per architecture)."""
    extracted = ExtractedText(text="")
    word = WordEntry(normalized_form="", word_type="")
    result = TranslationResult(translation="")

    assert extracted.text == ""
    assert word.normalized_form == ""
    assert word.word_type == ""
    assert result.translation == ""
```

Replace with:
```python
def test_all_models_accept_empty_strings() -> None:
    """Test all models accept empty strings (per architecture)."""
    extracted = ExtractedText(text="")
    word = Word(normalized_form="", word_type=PartOfSpeech.NOUN, language=Language.NL)

    assert extracted.text == ""
    assert word.normalized_form == ""
```

Note: `Word.word_type` cannot be empty string (it's a `PartOfSpeech` Enum), so we use a valid Enum value. The test now validates that `normalized_form` accepts empty strings. `Word.language` is a `Language` Enum and also cannot be empty string.

### Step 6: Update vulture whitelist

If T1 added `PartOfSpeech` and `Word` to `vulture_whitelist.py`, check if they are now detected as used (since T2 and T3 import them). Run:

```bash
uv run vulture nl_processing tests vulture_whitelist.py
```

If `PartOfSpeech` and `Word` are no longer flagged as unused, remove them from `vulture_whitelist.py`.

Also check if `WordEntry` or `TranslationResult` were in the whitelist -- they should NOT be (they were actively used before T2/T3, so never needed whitelisting). But verify.

### Step 7: Run verification

```bash
# Core unit tests
uv run pytest tests/unit/core/ -x -v
```

All tests must pass. The test file should now contain tests for:
- `Language` Enum (existing, unchanged)
- `ExtractedText` (existing, unchanged)
- `PartOfSpeech` Enum (added in T1)
- `Word` model (added in T1)
- `test_all_models_accept_empty_strings` (updated)

Then run the full check:

```bash
make check
```

This is critical because `make check` runs ALL tests including `extract_words_from_text` and `translate_word` modules. If removal of `WordEntry`/`TranslationResult` breaks anything, it will be caught here.

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Removing code, not adding.
- **Correct libraries only**: No library changes.
- **Correct file locations**: Editing existing files only.
- **No regressions**: `make check` runs all module tests. Any accidental remaining references to `WordEntry` or `TranslationResult` will cause import errors caught by the test suite.

## Error handling + correctness rules (mandatory)

- No error handling changes. Removing models that are no longer referenced.

## Zero legacy tolerance rule (mandatory)

- This task IS the legacy cleanup. After completion:
  - `WordEntry` is gone
  - `TranslationResult` is gone
  - All tests referencing them are removed or updated
  - No dead imports
  - No dead code

## Acceptance criteria (testable)

1. `WordEntry` class does not exist in `nl_processing/core/models.py`
2. `TranslationResult` class does not exist in `nl_processing/core/models.py`
3. `from nl_processing.core.models import WordEntry` raises `ImportError`
4. `from nl_processing.core.models import TranslationResult` raises `ImportError`
5. `nl_processing/core/models.py` contains exactly: `Language`, `PartOfSpeech`, `ExtractedText`, `Word`
6. `tests/unit/core/test_models.py` has no references to `WordEntry` or `TranslationResult`
7. `uv run pytest tests/unit/core/ -x -v` -- all pass
8. `make check` -- all pass (including all module tests)
9. No vulture warnings about unused code

## Verification / quality gates

- [ ] `WordEntry` removed from `nl_processing/core/models.py`
- [ ] `TranslationResult` removed from `nl_processing/core/models.py`
- [ ] No remaining references to `WordEntry` anywhere in codebase (verified by grep)
- [ ] No remaining references to `TranslationResult` anywhere in codebase (verified by grep)
- [ ] Old model tests removed from `tests/unit/core/test_models.py`
- [ ] `test_all_models_accept_empty_strings` updated to use `Word`
- [ ] Vulture whitelist cleaned up (no stale entries)
- [ ] `uv run pytest tests/unit/core/ -x -v` -- all pass
- [ ] `make check` -- all pass

## Edge cases

- `vulture_whitelist.py` might reference `WordEntry` or `TranslationResult` in an import -- check and remove if present. (Unlikely since they were actively used, but verify.)
- Other modules might have stale `__pycache__` files with old imports -- `make check` will catch this since it runs fresh pytest.

## Notes / risks

- **Risk**: A module not covered by this sprint (e.g., `translate_text`) might import `WordEntry` or `TranslationResult`.
  - **Mitigation**: Step 1 explicitly greps the entire codebase. If found, STOP and report. The `translate_text` module uses `TranslationResult`... actually no, looking at the code, `translate_text` has its own `TextTranslator` that works with `str` input/output, not `WordEntry`/`TranslationResult`. But verify with grep in Step 1 before deleting.
