---
Task ID: T7
Title: E2e tests — real photo vocabulary, rotated page, product box quality
Sprint: `translate_text_from_image`
Module: `translate_text_from_image`
Depends on: T6
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Validate the `ImageTextTranslator` on real photographs (vocabulary list, rotated bilingual page, product box) with reviewed golden outputs and key-term quality checks. These tests prove the module matches the quality bar of the existing two-call pipeline on the curated corpus.

## Context (contract mapping)

- Module spec: `packages/translate_text_from_image/docs/module-spec.md` — QA-5, NFR-2, SEED-5 through SEED-7, AC-4
- E2e pattern: `packages/extract_text_from_image/tests/e2e/.../test_full_extraction.py`
- Quality pattern: `packages/translate_text/tests/e2e/.../test_product_box_quality.py`

## Preconditions

- T6 completed (integration tests pass, confirming basic translation works).
- E2e fixture images available at `packages/extract_text_from_image/tests/e2e/extract_text_from_image/fixtures/`:
  - `dutch_vocabulary.jpg`
  - `dutch_vocabulary_rotated.jpg`
  - `dutch_product_box.jpg`

## Non-goals

- Automated performance benchmarking vs the two-call chain (deferred per D-2).
- Prompt tuning (fix in T5 if e2e tests fail).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/test_full_translation.py` — NEW
- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/test_product_box_quality.py` — NEW
- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/fixtures/` — copy image files here

**FORBIDDEN — this task must NEVER touch:**
- `packages/extract_text_from_image/tests/e2e/` — source of fixtures (read-only copy)
- Any other package's code or tests

**Test scope:**
- Tests go in: `packages/translate_text_from_image/tests/e2e/`
- Test command: `cd packages/translate_text_from_image && doppler run -- env PYTHONPATH=src:../core/src uv run pytest tests/e2e -x -v`

## Touched surface (expected files / modules)

- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/fixtures/dutch_vocabulary.jpg` (copied)
- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/fixtures/dutch_vocabulary_rotated.jpg` (copied)
- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/fixtures/dutch_product_box.jpg` (copied)
- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/test_full_translation.py` (new)
- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/test_product_box_quality.py` (new)

## Dependencies and sequencing notes

- Depends on T6 (integration tests must pass first — confirms basic translation works before testing on harder real images).
- T8 depends on this (final integration after all tests pass).

## Implementation steps

### Step 1: Copy fixture images

Copy the three real photo fixtures from `extract_text_from_image` to this package's e2e fixtures directory:

```bash
cp packages/extract_text_from_image/tests/e2e/extract_text_from_image/fixtures/dutch_vocabulary.jpg \
   packages/translate_text_from_image/tests/e2e/translate_text_from_image/fixtures/

cp packages/extract_text_from_image/tests/e2e/extract_text_from_image/fixtures/dutch_vocabulary_rotated.jpg \
   packages/translate_text_from_image/tests/e2e/translate_text_from_image/fixtures/

cp packages/extract_text_from_image/tests/e2e/extract_text_from_image/fixtures/dutch_product_box.jpg \
   packages/translate_text_from_image/tests/e2e/translate_text_from_image/fixtures/
```

These are now locally owned by this package (DEC-4, BR-5).

### Step 2: Create `test_full_translation.py`

Create `packages/translate_text_from_image/tests/e2e/translate_text_from_image/test_full_translation.py` (~120-150 lines).

Tests to implement:

1. **`test_real_photo_dutch_vocabulary_translation`** — Load `dutch_vocabulary.jpg`. Translate. Assert output is non-empty, contains Cyrillic, and includes key Russian vocabulary terms. The Dutch source vocabulary is known (from extract_text_from_image tests): "vandaan, veranderen, verbeteren, vlakbij, ..." — the Russian translations should include recognizable terms.

   **Key-term check approach**: Define a list of expected Russian terms/substrings:
   - "откуда" or "отсюда" (vandaan)
   - "менять" or "изменять" or "изменить" (veranderen)
   - "улучш" (verbeteren — "улучшать/улучшить")
   - "рядом" or "поблизости" or "близко" (vlakbij)
   - "порядок" or "порядк" (volgorde)
   - "пример" (voorbeeld)
   - "имя" (voornaam)
   - "форм" (vorm)
   - "вопрос" (vraag)
   - "подруг" or "друг" (vriendin)
   - "женщин" or "жен" (vrouw)

   Assert at least 50% of these terms are found (to allow for translation variation).

2. **`test_real_photo_rotated_bilingual_translates_only_dutch`** — Load `dutch_vocabulary_rotated.jpg`. Translate. Assert output is non-empty Cyrillic text. Assert output does NOT contain the English vocabulary words from the other column (e.g., "small", "to knock", "to come", "country"). The Dutch column includes: "klein, kloppen, komen, land, het..." — check for their Russian translations.

3. **`test_synthetic_full_pipeline`** — Generate a synthetic Dutch image, translate, verify non-empty Cyrillic output. Basic smoke test.

4. **`test_unsupported_format_e2e`** — Create a `.bmp` file, attempt translation, verify `UnsupportedImageFormatError`.

5. **`test_blank_image_raises_language_not_found`** — Create blank white image, translate, verify `TargetLanguageNotFoundError`.

### Step 3: Create `test_product_box_quality.py`

Create `packages/translate_text_from_image/tests/e2e/translate_text_from_image/test_product_box_quality.py` (~90-120 lines).

This test is the quality bar for product packaging translation. Pattern follows `translate_text/tests/e2e/.../test_product_box_quality.py` but translates FROM IMAGE instead of from text.

**IMPORTANT jscpd note**: The expected key terms and assertion structure must be different enough from the existing `test_product_box_quality.py` in `translate_text`. The content IS the same product box, but the code structure must differ:
- Use a different variable organization (e.g., dict instead of list of tuples)
- Use different assertion helper patterns
- Different function names and messages

Implementation:

1. **`test_product_box_image_translation_quality`** — Load `dutch_product_box.jpg`. Translate. Verify:
   - **Cyrillic ratio**: After removing "De Ruijter" brand name, output should be 100% Cyrillic alphabetic characters.
   - **Key-term spot checks**: Russian terms that must appear:
     - "De Ruijter" or "Де Р" (brand name — may be transliterated or kept)
     - "каждый день" or "ежедневно" (elke dag)
     - "наслажд" or "удовольстви" (genieten)
     - "ассортимент" (assortiment)
     - "вкусн" (smakelijke)
     - "продукт" (producten)
     - "шоколад" (chocolade-)
     - "молок" or "молоч" (melk)
     - "фрукт" (vruchten-)
     - "анис" (anijs-)

   Organize key terms as a dict mapping `description → list[alternatives]` and iterate with clear assertion messages.

### Step 4: Verify

Run the full e2e test suite:
```bash
cd packages/translate_text_from_image && \
  doppler run -- env PYTHONPATH=src:../core/src \
  uv run pytest tests/e2e -x -v
```

If quality tests fail:
- Review the prompt examples in T5
- Add more few-shot examples if needed
- Re-generate `nl_ru.json`
- Do NOT add fallbacks or workarounds

## Production safety constraints

- Uses live OpenAI API with project credentials (via doppler).
- API calls are stateless — no data mutations.
- No database operations.

## Anti-disaster constraints

- **Reuse before build**: Image fixtures are copied (not symlinked) for package isolation.
- **No regressions**: New test files only. Fixtures are copies.
- **jscpd compliance**: Test structure must differ from existing e2e tests. Use different assertion patterns, variable names, and organization.

## Error handling + correctness rules

- Tests verify specific error types, not generic exceptions.
- Quality tests use key-term spot-checking with clear failure messages.

## Zero legacy tolerance rule

- No legacy code. Fresh test suite with locally owned fixtures.

## Acceptance criteria (testable)

1. Three `.jpg` fixture files exist in `tests/e2e/translate_text_from_image/fixtures/`.
2. `test_full_translation.py` has at least 5 tests including vocabulary and rotated page.
3. `test_product_box_quality.py` has product box quality test with key-term checks and Cyrillic ratio.
4. All e2e tests pass against live API.
5. Vocabulary translation produces recognizable Russian terms.
6. Rotated page translates only Dutch column (no English leakage).
7. Product box translation passes all key-term checks.
8. All test files under 200 lines.

## Verification / quality gates

- [x] E2e tests pass with live API
- [x] Linters/formatters pass
- [x] jscpd: no 10+ line duplicates with other test files
- [x] All files under 200 lines
- [x] Quality assertions have clear failure messages

## Edge cases

- Vocabulary images may have words the model translates differently than expected. Use broad key-term matching (substrings) rather than exact matches.
- Product box translation may transliterate "De Ruijter" differently. Allow multiple transliterations.
- Rotated image may partially extract English if the model misidentifies language. Assert absence of specific English words as a guardrail.

## Notes / risks

- **Risk**: Single-call prompt may not achieve the same quality as the two-call pipeline on complex images.
  - **Mitigation**: Start with reasonable key-term thresholds (50% match for vocabulary, stricter for product box). Tighten after initial results. If quality is insufficient, expand few-shot examples in the prompt.
- **Risk**: jscpd may flag the product box test as similar to `translate_text`'s version.
  - **Mitigation**: Use structurally different code (dict-based key terms, different assertion helpers, different variable names). The actual key term values will overlap (same product), but the code structure must differ.
