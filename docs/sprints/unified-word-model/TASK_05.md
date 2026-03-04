---
Task ID: T5
Title: Update documentation to reflect unified Word model
Sprint: 2026-03-04_unified-word-model
Module: core + extract_words_from_text + translate_word (docs only)
Depends on: T4
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Update all architecture and PRD documentation to reflect the completed model unification. Remove all references to `WordEntry` and `TranslationResult`. Document the new `PartOfSpeech` Enum and `Word` model. Ensure documentation accurately describes the current codebase state.

## Context (contract mapping)

- Shared architecture: `docs/planning-artifacts/architecture.md`
- Module architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md`
- Module architecture: `nl_processing/translate_word/docs/architecture_translate_word.md`
- Module PRD: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md`
- Module PRD: `nl_processing/translate_word/docs/prd_translate_word.md`

## Preconditions

- T1-T4 completed: All code changes are done. `WordEntry` and `TranslationResult` no longer exist.
- `make check` passes 100% green

## Non-goals

- Do NOT modify any Python source code
- Do NOT modify any test files
- Do NOT modify any prompt generators or JSON files
- Do NOT create new documentation files -- only update existing ones

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `docs/planning-artifacts/architecture.md`
- `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md`
- `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md`
- `nl_processing/translate_word/docs/architecture_translate_word.md`
- `nl_processing/translate_word/docs/prd_translate_word.md`

**FORBIDDEN -- this task must NEVER touch:**
- Any Python source code file
- Any test file
- Any prompt file
- `vulture_whitelist.py`
- `Makefile`
- Any file not listed above

**Test scope:**
- No code tests. Documentation-only task.
- Verification: read the updated docs and confirm they match the code.

## Touched surface (expected files / modules)

- `docs/planning-artifacts/architecture.md` -- major updates to model descriptions, data flow, interface examples
- `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md` -- update model references
- `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md` -- update model references
- `nl_processing/translate_word/docs/architecture_translate_word.md` -- update model references, interface changes
- `nl_processing/translate_word/docs/prd_translate_word.md` -- update model references, interface changes

## Dependencies and sequencing notes

- Depends on T4: all code changes must be finalized before documenting the final state
- This is the last task in the sprint

## Implementation steps (developer-facing)

### Step 1: Update `docs/planning-artifacts/architecture.md`

This is the shared architecture document. Make the following targeted updates:

#### 1a. Update "Public Interface Pydantic Models" reference

Find (in section "Requirements Overview"):
```
Public Interface Pydantic Models (CFR7-11): ExtractedText, WordEntry, TranslationResult, Language enum
```
Replace with:
```
Public Interface Pydantic Models (CFR7-11): ExtractedText, Word, PartOfSpeech enum, Language enum
```

#### 1b. Update core package structure comment

Find (in section "Core Package Structure (Flat)"):
```
├── models.py            # PUBLIC interface models: ExtractedText, WordEntry, TranslationResult, Language
```
Replace with:
```
├── models.py            # PUBLIC interface models: ExtractedText, Word, PartOfSpeech, Language
```

#### 1c. Update Data Flow section

Find:
```
         markdown text → [extract_words_from_text] → list[WordEntry]
         markdown text → [translate_text] → translated text
         list[str] → [translate_word] → list[TranslationResult]
```
Replace with:
```
         markdown text → [extract_words_from_text] → list[Word]
         markdown text → [translate_text] → translated text
         list[Word] → [translate_word] → list[Word]
```

#### 1d. Update Requirements Coverage table

Find (in "Functional Requirements Coverage"):
```
| CFR7-11 (Pydantic models) | `core/models.py` — public interface models only |
```
Replace with:
```
| CFR7-11 (Pydantic models) | `core/models.py` — `ExtractedText`, `Word`, `PartOfSpeech` enum, `Language` enum |
```

#### 1e. Update "Module Public Interface Pattern" section

Find (in the section that shows example callers):
No changes needed to the import examples (they show `service` imports, not model imports).

Find the pattern section that mentions return types:
```
- Return types use `core` public models where applicable
```
This is still true. No change needed.

### Step 2: Update `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md`

#### 2a. Update "Flat Word-Type Taxonomy" decision

Find:
```
### Decision: Flat Word-Type Taxonomy

Word types are flat strings (`"noun"`, `"verb"`, `"adjective"`, `"preposition"`, `"conjunction"`, `"proper_noun_person"`, `"proper_noun_country"`, etc.) — not enums, not hierarchical structures.

**Rationale:** Flat strings allow the LLM to assign types naturally via the prompt, and callers can filter by simple string comparison. The taxonomy is extensible via prompts — adding a new type (e.g., `"proper_noun_city"`) requires only a prompt update, no code change.
```

Replace with:
```
### Decision: PartOfSpeech Enum Word-Type Taxonomy

Word types use the `PartOfSpeech` Enum from `core/models.py`. Allowed values: `noun`, `verb`, `adjective`, `adverb`, `preposition`, `conjunction`, `pronoun`, `article`, `numeral`, `proper_noun_person`, `proper_noun_country`.

**Rationale:** Using an Enum instead of free-form strings provides compile-time type safety and Pydantic validation. The LLM returns word types as strings matching the Enum values; Pydantic automatically coerces them. Invalid word types are rejected at validation time (fail fast). The Enum is extensible — adding a new value (e.g., `PROPER_NOUN_CITY`) requires adding it to the Enum and updating the prompt, with no other code changes.
```

#### 2b. Update "Compound Expressions" decision reference

Find:
```
The output list may contain multi-word entries. The `normalized_form` field in `WordEntry` can be a phrase
```
Replace with:
```
The output list may contain multi-word entries. The `normalized_form` field in `Word` can be a phrase
```

#### 2c. Update "Empty List for Non-Target Language" decision

Find:
```
the module returns an empty `list[WordEntry]`
```
Replace with:
```
the module returns an empty `list[Word]`
```

#### 2d. Update "Set-Based Test Validation" decision

Find:
```
Quality tests use set comparison (normalized form + word type)
```
This is still accurate. No change needed (the comparison now uses `.word_type.value` but the concept is the same).

#### 2e. Update "Test Strategy" section

Find:
```
- **Unit tests:** Mock LangChain chain invocation. Test that module correctly passes text to chain and returns `list[WordEntry]`.
```
Replace with:
```
- **Unit tests:** Mock LangChain chain invocation. Test that module correctly passes text to chain and returns `list[Word]`.
```

### Step 3: Update `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md`

#### 3a. Update Executive Summary

Find:
```
it returns a flat list of `WordEntry` objects (from `core`) containing a normalized form and a word type.
```
Replace with:
```
it returns a flat list of `Word` objects (from `core`) containing a normalized form, a `PartOfSpeech` word type, and a language.
```

#### 3b. Update Journey 1 description

Find:
```
Gets a flat list of `WordEntry` objects: each word normalized
```
Replace with:
```
Gets a flat list of `Word` objects: each word normalized
```

#### 3c. Update Journey Requirements Summary

Find:
```
| Single extraction method (text in, `WordEntry` objects out) | Journey 1 |
```
Replace with:
```
| Single extraction method (text in, `Word` objects out) | Journey 1 |
```

#### 3d. Update API Surface section

Find:
```
**Return type:** flat list of `WordEntry` objects (from `core`), each containing:
- `normalized_form` — normalized word (e.g., "de fiets", "lopen")
- `word_type` — flat type string (e.g., noun, verb, adjective, preposition, proper_noun_person, proper_noun_country, conjunction, etc.)
```
Replace with:
```
**Return type:** flat list of `Word` objects (from `core`), each containing:
- `normalized_form` — normalized word (e.g., "de fiets", "lopen")
- `word_type` — `PartOfSpeech` Enum value (e.g., `NOUN`, `VERB`, `ADJECTIVE`, `PREPOSITION`, `PROPER_NOUN_PERSON`, `PROPER_NOUN_COUNTRY`)
- `language` — `Language` Enum value (set programmatically by the service, e.g., `Language.NL`)
```

#### 3e. Update FR9

Find:
```
- FR9: Each `WordEntry` contains a normalized form and a word type
```
Replace with:
```
- FR9: Each `Word` contains a normalized form, a `PartOfSpeech` word type, and a language
```

#### 3f. Update FR11

Find:
```
- FR11: Word types are flat strings — no nested structures or hierarchies
```
Replace with:
```
- FR11: Word types are `PartOfSpeech` Enum values — type-safe, validated by Pydantic
```

### Step 4: Update `nl_processing/translate_word/docs/architecture_translate_word.md`

#### 4a. Update "One-to-One Order-Preserving Mapping" decision

Find:
```
The output `list[TranslationResult]` must have exactly `len(output) == len(input)`
```
Replace with:
```
The output `list[Word]` must have exactly `len(output) == len(input)`
```

#### 4b. Update "Source + Target Language Constructor" decision

Find:
```python
translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)
```
This is still correct. No change needed.

#### 4c. Replace "TranslationResult — Minimal Pydantic Model, Extensible" decision

Find the entire decision:
```
### Decision: `TranslationResult` — Minimal Pydantic Model, Extensible

`TranslationResult` (from `core`) currently contains only `translation: str`. It is a Pydantic model (not a plain string) to enable future field additions (usage examples, synonyms, alternative translations) without breaking the public interface.
```

Replace with:
```
### Decision: Unified `Word` Model for Input and Output

The translator accepts `list[Word]` as input and returns `list[Word]` as output. Input words have `language=Language.NL`; output words have `language=Language.RU`. Each output `Word` contains `normalized_form` (the Russian translation), `word_type` (a `PartOfSpeech` Enum value determined by the LLM for the target language), and `language` (set programmatically by the service to the target language).

**Rationale:** Using the same `Word` model for both extraction and translation creates a unified pipeline where the output of `extract_words_from_text` flows directly into `translate_word` without type conversion.
```

#### 4d. Update "Test Strategy" section

Find:
```
- **Unit tests:** Mock LangChain chain invocation. Test empty-input handling, one-to-one mapping enforcement, error mapping.
```
Replace with:
```
- **Unit tests:** Mock LangChain chain invocation. Test `list[Word]` input/output, empty-input handling, one-to-one mapping enforcement, error mapping.
```

Find:
```
- **E2e tests:** Full translation scenarios with word lists from upstream pipeline.
```
Replace with:
```
- **E2e tests:** Full translation scenarios with `list[Word]` inputs representing upstream pipeline output.
```

### Step 5: Update `nl_processing/translate_word/docs/prd_translate_word.md`

#### 5a. Update Executive Summary

Find:
```
It accepts a list of normalized source-language words/phrases and returns a list of `TranslationResult` objects (from `core`) — one-to-one, preserving input order.
```
Replace with:
```
It accepts a list of `Word` objects (from `core`) and returns a list of `Word` objects — one-to-one, preserving input order.
```

Find:
```
`TranslationResult` currently contains only a `translation` field, designed for future field extensions without breaking the interface.
```
Replace with:
```
Each output `Word` contains the Russian `normalized_form`, a `PartOfSpeech` word type determined by the LLM, and `language=Language.RU`.
```

#### 5b. Update "What Makes This Special"

Find:
```
- **Extensible result objects:** `TranslationResult` (from `core`) is a Pydantic model ready for future field additions without API changes
```
Replace with:
```
- **Unified pipeline model:** Uses the same `Word` model as `extract_words_from_text`, creating a seamless pipeline from extraction to translation
```

#### 5c. Update Success Criteria

Find:
```
- **Output structure:** Each input word maps to exactly one `TranslationResult` in the output list, preserving order
```
Replace with:
```
- **Output structure:** Each input `Word` maps to exactly one output `Word` in the output list, preserving order
```

#### 5d. Update Journey 1 code example

Find:
```python
translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)
results = translator.translate(["huis", "lopen", "snel"])
# results[0].translation → "дом"
```
Replace with:
```python
translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)
words = [Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL), ...]
results = translator.translate(words)
# results[0].normalized_form → "дом"
# results[0].word_type → PartOfSpeech.NOUN
# results[0].language → Language.RU
```

#### 5e. Update Journey Requirements Summary

Find:
```
| Single translate method: `list[str]` → `list[TranslationResult]` | Success path |
```
Replace with:
```
| Single translate method: `list[Word]` → `list[Word]` | Success path |
```

#### 5f. Update API Surface

Find:
```
- Method: `translate(words: list[str]) -> list[TranslationResult]` — `TranslationResult` from `core`
```
Replace with:
```
- Method: `translate(words: list[Word]) -> list[Word]` — `Word` from `core`
```

Find:
```
`Language`, `TranslationResult`, and `APIError` are imported from `core`.
```
Replace with:
```
`Language`, `Word`, `PartOfSpeech`, and `APIError` are imported from `core`.
```

#### 5g. Update Implementation Considerations

Find:
```
- Pydantic `TranslationResult` model defined in `core` — serves dual purpose: public API return type and LangChain tool calling schema
```
Replace with:
```
- Pydantic `Word` model defined in `core` — used as public API input/output type. Internal `_LLMTranslationEntry` model (without `language` field) used for LangChain tool calling
```

#### 5h. Update Functional Requirements

Find:
```
- FR2: Developer can call a single translate method with a list of normalized words/phrases and receive a list of `TranslationResult` objects
```
Replace with:
```
- FR2: Developer can call a single translate method with a list of `Word` objects and receive a list of `Word` objects
```

Find:
```
- FR4: System returns `TranslationResult` objects (from `core`) containing a `translation` field
```
Replace with:
```
- FR4: System returns `Word` objects (from `core`) containing `normalized_form`, `word_type` (`PartOfSpeech`), and `language`
```

### Step 6: Verification

After all documentation changes:

1. Read each updated file and verify that no references to `WordEntry` or `TranslationResult` remain (except in historical context if explicitly needed, which shouldn't be the case).

2. Verify internal consistency: the data flow described in shared architecture matches the interfaces described in module architectures and PRDs.

3. Run `make check` one final time to confirm no code was accidentally modified:

```bash
make check
```

## Production safety constraints (mandatory)

- **Database operations**: None. Documentation only.
- **Resource isolation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Editing existing docs, not creating new ones.
- **Correct file locations**: All changes in existing documentation files.
- **No regressions**: No code changes. `make check` verifies nothing broke.

## Error handling + correctness rules (mandatory)

- N/A for documentation task.

## Zero legacy tolerance rule (mandatory)

- All references to `WordEntry` and `TranslationResult` must be removed from documentation.
- Data flow diagrams must reflect the current code state.
- Interface descriptions must match the actual code signatures.

## Acceptance criteria (testable)

1. No references to `WordEntry` in any of the 5 documentation files
2. No references to `TranslationResult` in any of the 5 documentation files
3. Data flow in shared architecture shows `list[Word]` for both extraction and translation
4. `translate_word` interface documented as `list[Word] -> list[Word]`
5. `extract_words_from_text` interface documented as returning `list[Word]`
6. `PartOfSpeech` Enum documented in shared architecture
7. Each doc file is internally consistent (no contradictory statements)
8. `make check` still passes (no accidental code changes)

## Verification / quality gates

- [ ] `docs/planning-artifacts/architecture.md` -- all `WordEntry`/`TranslationResult` references updated
- [ ] `architecture_extract_words_from_text.md` -- all references updated
- [ ] `prd_extract_words_from_text.md` -- all references updated
- [ ] `architecture_translate_word.md` -- all references updated
- [ ] `prd_translate_word.md` -- all references updated
- [ ] No stale model references remain in any doc
- [ ] Data flow diagram is accurate
- [ ] `make check` passes

## Edge cases

- Documentation may contain references in frontmatter YAML that mention old models -- check the `inputDocuments` and other metadata fields. These are file paths, not model names, so they should be fine.
- Markdown link references should still work after text changes.

## Notes / risks

- **Risk**: Missing a `WordEntry` or `TranslationResult` reference in a doc file.
  - **Mitigation**: After updating, grep each file for both strings to verify zero occurrences.
