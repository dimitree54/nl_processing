---
Task ID: `T14`
Title: `Integration tests for sampling module against real DB`
Sprint: `2026-03-04_database-and-sampling`
Module: `sampling`
Depends on: `T12, T10`
Parallelizable: `no`
Owner: `Developer`
Status: `done`
---

## Goal / value

Integration tests validate that WordSampler works end-to-end against a real Neon database with pre-populated word pairs and exercise scores. Confirms that the sampling distribution responds to real score data.

## Context (contract mapping)

- Requirements: `nl_processing/sampling/docs/prd_sampling.md` — NFR1 (performance), success criteria
- Architecture: `nl_processing/sampling/docs/architecture_sampling.md` — Test Strategy: Integration tests

## Preconditions

- T12 complete (WordSampler implementation)
- T10 complete (integration test infrastructure for database — conftest patterns, reset/teardown)
- T8 complete (testing utilities)
- Doppler `dev` environment configured

## Non-goals

- No mocking — real database
- No e2e translation flow (words are pre-inserted directly via backend)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `tests/integration/sampling/` — create directory + test files
- `tests/integration/sampling/__init__.py` — create (empty)
- `tests/integration/sampling/conftest.py` — create (DB fixtures with pre-populated data)
- `tests/integration/sampling/test_weighted_sampling.py` — weighted sampling tests
- `tests/integration/sampling/test_adversarial_sampling.py` — adversarial sampling tests

**FORBIDDEN — this task must NEVER touch:**

- Any module source code
- Tests for other modules
- Production database

**Test scope:**

- Tests go in: `tests/integration/sampling/`
- Test command: `doppler run -- uv run pytest -n auto tests/integration` (runs as part of `make check`)

## Touched surface (expected files / modules)

- `tests/integration/sampling/__init__.py` (new, empty)
- `tests/integration/sampling/conftest.py` (new)
- `tests/integration/sampling/test_weighted_sampling.py` (new)
- `tests/integration/sampling/test_adversarial_sampling.py` (new)

## Dependencies and sequencing notes

- Depends on T12 (WordSampler) and T10 (DB integration infra works)
- This is the final task — no downstream dependencies

## Third-party / library research (mandatory for any external dependency)

- **Library**: pytest + pytest-asyncio (already installed)
- **Service**: Neon PostgreSQL (dev) via Doppler

## Implementation steps (developer-facing)

1. **Create `tests/integration/sampling/` directory with `__init__.py` (empty).**

2. **Create `tests/integration/sampling/conftest.py`:**
   - Session-scoped async fixture: `reset_database` at start, `drop_all_tables` at end
   - Module-scoped fixture: pre-populate the database with a known set of word pairs:
     - Insert 10+ Dutch words directly into `words_nl` via NeonBackend
     - Insert corresponding Russian translations into `words_ru`
     - Create translation links in `translations_nl_ru`
     - Create user-word associations in `user_words` for test user
     - Set known exercise scores: some words with positive scores, some with zero/negative
   - This avoids needing real translation (no OpenAI API calls) — words and translations are inserted directly
   - Ensure a mix of part-of-speech types (nouns, verbs, adjectives) for adversarial tests

3. **Create `tests/integration/sampling/test_weighted_sampling.py`:**
   - Test: `sample(5)` returns 5 unique WordPairs from the test user's dictionary
   - Test: `sample` with all zero scores returns items with roughly uniform distribution (statistical check over 100 runs)
   - Test: `sample` with mixed scores — words with non-positive scores sampled significantly more often than positive-scored words (statistical check over 500 runs)
   - Test: `sample(100)` when user has only 10 words → returns all 10
   - Test: `sample(0)` returns `[]`
   - Test: verify returned WordPairs have correct Word fields (language, word_type, normalized_form)

4. **Create `tests/integration/sampling/test_adversarial_sampling.py`:**
   - Test: `sample_adversarial(noun_word, 3)` returns only noun WordPairs
   - Test: `sample_adversarial` excludes the source word
   - Test: `sample_adversarial(verb_word, 100)` with only 2 other verbs → returns 2
   - Test: `sample_adversarial` with no matching POS → returns `[]`

5. **200-line limit per file**: 2 test files + conftest. Stay under 200 lines each.

6. Run `doppler run -- make check` — all tests pass.

## Production safety constraints (mandatory)

- **Database operations**: All against dev Neon database via Doppler.
- **API calls**: None — word data is pre-inserted directly, no translation API calls needed.
- **Resource isolation**: Dev database only.
- **Cleanup**: `drop_all_tables` in teardown.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses testing utilities from T8 and patterns from T10.
- **No regressions**: New test files only.

## Error handling + correctness rules (mandatory)

- Tests use real DB — failures indicate real bugs.
- Statistical tests use generous tolerance to avoid flakiness.
- No `pytest.skip`.

## Zero legacy tolerance rule (mandatory)

- No old test files.

## Acceptance criteria (testable)

1. `tests/integration/sampling/` directory exists with conftest and 2 test files.
2. All test files under 200 lines.
3. conftest pre-populates DB with known word pairs and scores (no API calls).
4. Weighted sampling tests verify distribution responds to scores.
5. Adversarial sampling tests verify POS filtering and source word exclusion.
6. Dev database left clean after tests.
7. `make check` passes (all existing + all new tests).

## Verification / quality gates

- [ ] Test directory created with DB-populating conftest
- [ ] Weighted sampling distribution test passes
- [ ] Adversarial sampling filtering test passes
- [ ] Dev database clean after run
- [ ] All files under 200 lines
- [ ] `make check` passes (full suite green)

## Edge cases

- pytest-xdist may run sampling integration tests in parallel with database integration tests — use unique user_id to avoid conflicts.
- Statistical distribution tests — use `random.seed` or large sample sizes for robustness.
- Pre-populated fixture data must include enough variety (multiple POS types, multiple score levels).

## Notes / risks

- **Risk**: Pre-populating DB directly bypasses DatabaseService, which might create data inconsistencies.
  - **Mitigation**: Insert data via NeonBackend methods (same SQL as DatabaseService uses). The data shape is identical.
- **Risk**: Statistical test flakiness.
  - **Mitigation**: Large sample sizes (500+ runs for weighted test). Generous tolerance (e.g., non-positive words sampled >3x more often).
