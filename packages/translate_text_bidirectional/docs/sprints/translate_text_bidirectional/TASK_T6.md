---
Task ID: `T6`
Title: `E2E tests — full translation and quality assertions, both directions`
Sprint: `2026-03-12_translate-text-bidirectional`
Module: `translate_text_bidirectional`
Depends on: `T5`
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Create end-to-end tests that exercise the full translation pipeline with hard quality assertions in both directions. These mirror the existing `translate_text` e2e test suite (full-markdown translation, short sentences, product-box quality with key-term checking, unsupported-pair init failure) and extend each scenario bidirectionally. After this task, the module has the same quality coverage bar as `translate_text` — for both NL→RU and RU→NL.

## Context (contract mapping)

- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md` — FR-12, DEC-5, AC-1 through AC-7, QA-9
- Reference: `packages/translate_text/tests/e2e/translate_text/test_full_translation.py`
- Reference: `packages/translate_text/tests/e2e/translate_text/test_product_box_quality.py`
- Testing strategy: E2E tests run via `doppler run --` for API credentials

## Preconditions

- T4 completed (service implemented and unit tested).
- T5 completed (integration tests passing, confirming live API works in both directions).

## Non-goals

- Unit tests (T4).
- Integration tests (T5).
- Mixed-language input e2e coverage (deferred per spec).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/translate_text_bidirectional/tests/e2e/translate_text_bidirectional/` — e2e test files

**FORBIDDEN — this task must NEVER touch:**
- `packages/translate_text/` — reference only
- `packages/core/` — no changes
- `packages/translate_text_bidirectional/src/` — no service changes
- Any other package

**Test scope:**
- Tests go in: `packages/translate_text_bidirectional/tests/e2e/translate_text_bidirectional/`
- Test command: `make check` from `packages/translate_text_bidirectional/` (e2e tests run via doppler)

## Touched surface (expected files / modules)

- `packages/translate_text_bidirectional/tests/e2e/translate_text_bidirectional/test_full_translation.py`
- `packages/translate_text_bidirectional/tests/e2e/translate_text_bidirectional/test_product_box_quality.py`

## Dependencies and sequencing notes

- Depends on T5 (integration tests confirm API connectivity and basic quality).
- T7 depends on all tests passing.

## Third-party / library research (mandatory for any external dependency)

- Same as T5 — `pytest-asyncio`, OpenAI API via Doppler.
- No new dependencies.

## Implementation steps (developer-facing)

### File 1: `test_full_translation.py`

Mirror `translate_text/tests/e2e/translate_text/test_full_translation.py` with bidirectional coverage.

1. **`test_full_translation_nl_to_ru`** — Translate multi-paragraph Dutch markdown (heading, subheadings, bold, italic, list). Assert non-empty string output.

2. **`test_full_translation_ru_to_nl`** — Translate multi-paragraph Russian markdown (equivalent structure). Assert non-empty string output.

3. **`test_empty_input_handling`** — `translate("")` returns `""`.

4. **`test_markdown_heavy_nl_to_ru`** — Translate markdown-heavy Dutch text. Assert `#`, `**`, `- ` in output.

5. **`test_markdown_heavy_ru_to_nl`** — Translate markdown-heavy Russian text. Assert `#`, `**`, `- ` in output.

6. **`test_short_sentence_nl_to_ru`** — Translate "Goede morgen, hoe gaat het?". Assert non-empty.

7. **`test_short_sentence_ru_to_nl`** — Translate "Доброе утро, как дела?". Assert non-empty.

8. **`test_unsupported_pair_raises_at_init`** — `BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.NL)` raises `ValueError`.

### File 2: `test_product_box_quality.py`

Mirror `translate_text/tests/e2e/translate_text/test_product_box_quality.py` with bidirectional key-term assertions.

9. **`test_product_box_nl_to_ru_quality`** — Translate the De Ruijter product box text (Dutch→Russian). Use the same key-term spot-checking approach:
   - Define `EXPECTED_KEY_TERMS_NL_TO_RU` — list of `(description, [alternative_substrings])`.
   - Reuse the same key terms from the reference test (brand name, "каждый день", "наслаждаться", "ассортимент", "вкусн", "продукт", "шоколад", "молок", "фрукт", "анис", "бел", "голуб/син", "розов").
   - Cyrillic ratio check (same pattern as reference).

10. **`test_product_box_ru_to_nl_quality`** — Translate a comparable Russian product description text back to Dutch. Define direction-appropriate assertions:
    - Create a Russian product text (can be the expected Russian translation of the De Ruijter text, or a comparable Russian product description).
    - Define `EXPECTED_KEY_TERMS_RU_TO_NL` — list of `(description, [alternative_dutch_substrings])`.
    - Key terms to check: product-related Dutch words like "chocolade", "melk", "producten", "assortiment", "smakelijk/lekker", "genieten".
    - Latin ratio check (inverse of Cyrillic check — output should be predominantly Latin).

### General

11. **Run `make check`** — all e2e tests pass via `doppler run`.

12. **Monitor file sizes** — if either file approaches 200 lines, extract shared helpers (e.g., key term checking logic) into a test helper module within the e2e directory.

## Production safety constraints (mandatory)

- No database operations.
- OpenAI API calls use Doppler-managed credentials.
- No shared local resources affected.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Mirrors `translate_text` e2e patterns. Reuses key-term spot-checking approach.
- **Correct libraries only**: `pytest`, `pytest-asyncio`, `re` (stdlib).
- **No regressions**: Only new test files added.

## Error handling + correctness rules (mandatory)

- E2E tests use hard assertions, not manual review checkpoints (per spec).
- Key-term failures produce detailed error messages listing which terms were missing.
- Cyrillic/Latin ratio checks produce clear failure messages.

## Zero legacy tolerance rule (mandatory)

- No legacy exists — fresh test files.

## Acceptance criteria (testable)

1. `test_full_translation.py` covers: full NL→RU, full RU→NL, empty input, markdown-heavy both directions, short sentence both directions, unsupported pair init failure.
2. `test_product_box_quality.py` covers: NL→RU key-term quality, RU→NL key-term quality, script ratio checks.
3. All e2e tests pass via `doppler run -- pytest tests/e2e -x -v`.
4. Key-term assertions are hard (fail CI if terms missing), not manual checkpoints.
5. `make check` passes completely from package directory.
6. All files under 200 lines.

## Verification / quality gates

- [ ] E2E tests pass via `doppler run -- pytest tests/e2e -x -v`
- [ ] Full translation produces non-empty output both directions
- [ ] Markdown symbols preserved in both directions
- [ ] Product-box NL→RU key terms all present
- [ ] Product-box RU→NL key terms all present
- [ ] Script ratio checks pass (Cyrillic for NL→RU, Latin for RU→NL)
- [ ] Unsupported pair raises ValueError
- [ ] Linters pass on test files
- [ ] Files under 200 lines

## Edge cases

- Product box text contains brand name "De Ruijter" — Latin chars in Cyrillic output. Exclude brand name from ratio check (same pattern as reference).
- RU→NL quality assertions need Dutch key terms that are stable across translations (use common words, accept synonyms via alternative lists).
- Russian product text must be natural Russian, not machine-translated — use a well-known Russian product description or the expected output from the NL→RU translation.

## Notes / risks

- **Risk**: RU→NL quality assertions are harder to define because we don't have a known-good Dutch translation to reference (unlike NL→RU where we know the Dutch source).
  - **Mitigation**: Use broader alternative lists for Dutch key terms. Accept common synonyms. Focus on structural correctness rather than exact wording.
- **Risk**: E2E test files may approach 200 lines due to key-term constant lists.
  - **Mitigation**: Keep constant lists compact. If needed, extract into a shared test data module.
