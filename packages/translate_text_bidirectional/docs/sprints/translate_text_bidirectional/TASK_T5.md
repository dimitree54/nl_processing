---
Task ID: `T5`
Title: `Integration tests — live API, both directions`
Sprint: `2026-03-12_translate-text-bidirectional`
Module: `translate_text_bidirectional`
Depends on: `T4`
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Create integration tests that verify the `BidirectionalTextTranslator` against the live OpenAI API in both directions (NL→RU and RU→NL). These tests validate output cleanliness, script correctness, markdown preservation, performance, and non-supported-language handling. After this task, the module has live-API confidence for both translation directions.

## Context (contract mapping)

- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md` — FR-3 through FR-8, NFR-1, QA-2 through QA-6
- Reference: `packages/translate_text/tests/integration/translate_text/test_translation_quality.py`
- Testing strategy: Integration tests run via `doppler run --` for API credentials

## Preconditions

- T4 completed (`BidirectionalTextTranslator` is implemented and unit tests pass).
- OpenAI API key available via Doppler for integration test runs.

## Non-goals

- Unit tests (completed in T4).
- E2E tests with hard quality assertions (T6).
- Testing mixed-language input (deferred per spec, not a v1 acceptance gate).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/translate_text_bidirectional/tests/integration/translate_text_bidirectional/` — integration test files

**FORBIDDEN — this task must NEVER touch:**
- `packages/translate_text/` — reference only
- `packages/core/` — no changes
- `packages/translate_text_bidirectional/src/` — no service changes
- Any other package

**Test scope:**
- Tests go in: `packages/translate_text_bidirectional/tests/integration/translate_text_bidirectional/`
- Test command: `make check` from `packages/translate_text_bidirectional/` (integration tests run via doppler)

## Touched surface (expected files / modules)

- `packages/translate_text_bidirectional/tests/integration/translate_text_bidirectional/test_translation_quality.py`

## Dependencies and sequencing notes

- Depends on T4 (working service with unit tests).
- T6 depends on integration tests passing.

## Third-party / library research (mandatory for any external dependency)

- **Service**: OpenAI API (via `langchain-openai` ChatOpenAI)
  - **Rate limits**: Tier-dependent; `service_tier="priority"` default avoids most rate limiting.
  - **Latency**: Typical <5s for short text with `gpt-4.1-mini`.
- **Library**: `pytest-asyncio` (`>=1.3.0,<2`) — `@pytest.mark.asyncio` for async tests.
- **Tool**: Doppler — `doppler run --` injects `OPENAI_API_KEY` for integration/e2e tests.

## Implementation steps (developer-facing)

1. **Create `test_translation_quality.py`** in `tests/integration/translate_text_bidirectional/`. Mirror the structure of `translate_text/tests/integration/translate_text/test_translation_quality.py` but with bidirectional coverage.

2. **Define LLM chatter prefixes** (same list as reference):
   ```python
   LLM_CHATTER_PREFIXES = [
       "Here is", "Translation:", "Sure,", "Of course",
       "The translation", "Below is", "Certainly",
   ]
   ```

3. **Implement NL→RU direction tests**:
   - `test_nl_to_ru_output_cleanliness` — Translate a Dutch sentence. Assert non-empty, no LLM chatter prefixes.
   - `test_nl_to_ru_cyrillic_only_output` — Translate a simple Dutch sentence (no proper nouns). Assert output contains no Latin characters (only Cyrillic + punctuation).
   - `test_nl_to_ru_markdown_structure_preservation` — Translate Dutch markdown with heading, bold, italic, list. Assert `#`, `**`, `- ` present in output.

4. **Implement RU→NL direction tests**:
   - `test_ru_to_nl_output_cleanliness` — Translate a Russian sentence. Assert non-empty, no LLM chatter prefixes.
   - `test_ru_to_nl_latin_only_output` — Translate a simple Russian sentence (no proper nouns). Assert output contains no Cyrillic characters (only Latin + punctuation).
   - `test_ru_to_nl_markdown_structure_preservation` — Translate Russian markdown with heading, bold, italic, list. Assert `#`, `**`, `- ` present in output.

5. **Implement edge case tests**:
   - `test_non_dutch_or_russian_text_returns_empty` — Translate English text. Assert result is `""`.
   - `test_performance_nl_to_ru` — Translate ~100-word Dutch text. Assert completes in <5 seconds (NFR-1).
   - `test_performance_ru_to_nl` — Translate ~100-word Russian text. Assert completes in <5 seconds.

6. **Run `make check`** from the package directory. Integration tests run via `doppler run --`.

7. **Verify** all files stay under 200 lines. If the test file approaches 200 lines, split NL→RU and RU→NL tests into separate files:
   - `test_nl_to_ru_quality.py`
   - `test_ru_to_nl_quality.py`

## Production safety constraints (mandatory)

- No database operations.
- OpenAI API calls use Doppler-managed credentials (test/dev environment).
- No shared local resources affected.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Mirrors `translate_text` integration test patterns exactly.
- **Correct libraries only**: `pytest`, `pytest-asyncio` (from dev dependencies).
- **No regressions**: Only new test files added; no existing code modified.

## Error handling + correctness rules (mandatory)

- Tests must assert concrete conditions, not just "no exception".
- Performance assertions use explicit time bounds (5s).
- Script checks use regex patterns for character class validation.

## Zero legacy tolerance rule (mandatory)

- No legacy exists — fresh test files.

## Acceptance criteria (testable)

1. NL→RU integration tests pass: output is non-empty Cyrillic, no chatter, markdown preserved.
2. RU→NL integration tests pass: output is non-empty Latin, no chatter, markdown preserved.
3. Non-Dutch/Russian input returns `""`.
4. Performance: both directions complete <5s for ~100-word input.
5. All integration tests pass via `make check` (which uses `doppler run`).
6. All files under 200 lines.

## Verification / quality gates

- [ ] Integration tests pass via `doppler run -- pytest tests/integration -x -v`
- [ ] NL→RU output is Cyrillic-only for proper-noun-free input
- [ ] RU→NL output is Latin-only for proper-noun-free input
- [ ] Markdown symbols preserved in both directions
- [ ] No LLM chatter prefixes in output
- [ ] Performance under 5s per direction
- [ ] Non-NL/RU input returns empty string
- [ ] Linters pass on test files
- [ ] Files under 200 lines

## Edge cases

- Russian text with Latin brand names (e.g., "iPhone") — the Latin-only check should use a proper-noun-free test input to avoid false negatives.
- Very short input (1-2 words) — may be ambiguous for direction detection. Integration tests use complete sentences to avoid this.

## Notes / risks

- **Risk**: API latency spikes could cause performance test flakiness.
  - **Mitigation**: 5s is generous for gpt-4.1-mini on short text. If flaky, consider increasing to 10s.
- **Risk**: Model may occasionally include minor chatter. The chatter prefix list is comprehensive but not exhaustive.
  - **Mitigation**: Same list used by `translate_text` — proven stable. Prompt few-shot examples reinforce clean output.
