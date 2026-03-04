---
Task ID: `T12`
Title: `Implement WordSampler in sampling module`
Sprint: `2026-03-04_database-and-sampling`
Module: `sampling`
Depends on: `T6`
Parallelizable: `yes, with T10 and T11`
Owner: `Developer`
Status: `planned`
---

## Goal / value

`WordSampler` is the sole public class of the `sampling` module. It provides weighted random sampling of practice items based on exercise scores, and adversarial distractor sampling for multiple-choice exercises.

## Context (contract mapping)

- Requirements: `nl_processing/sampling/docs/prd_sampling.md` — FR1-FR20 (all functional requirements)
- Architecture: `nl_processing/sampling/docs/architecture_sampling.md` — all decisions
- Product brief: `nl_processing/sampling/docs/product-brief-sampling-2026-03-04.md`

## Preconditions

- T6 complete (ExerciseProgressStore with `get_word_pairs_with_scores`)
- T2 complete (models — WordPair, ScoredWordPair)
- `nl_processing/sampling/` directory exists with `docs/` subdirectory

## Non-goals

- No spaced repetition algorithms
- No LLM calls
- No database writes
- No unit tests (that's T13)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/sampling/__init__.py` — create (empty)
- `nl_processing/sampling/service.py` — create

**FORBIDDEN — this task must NEVER touch:**

- `nl_processing/database/` source files
- Any other module's code or tests
- `nl_processing/sampling/docs/` (documentation, read-only)

**Test scope:**

- No new tests in this task (T13 handles unit tests, T14 handles integration)
- `make check` must pass

## Touched surface (expected files / modules)

- `nl_processing/sampling/__init__.py` (new, empty)
- `nl_processing/sampling/service.py` (new)

## Dependencies and sequencing notes

- Depends on T6 (ExerciseProgressStore provides scored word pairs)
- T13 (sampling unit tests) depends on this
- T14 (sampling integration tests) depends on this + T10
- Can run in parallel with T10 and T11

## Third-party / library research (mandatory for any external dependency)

- **Library**: Python `random` module (stdlib)
  - **Docs**: https://docs.python.org/3.12/library/random.html
  - `random.choices(population, weights, k)` — weighted sampling WITH replacement
  - For without-replacement weighted sampling: use iterative selection with weight adjustment, or `random.choices` with deduplication loop
  - **Recommended approach**: Iterative selection — pick one item via `random.choices(weights=...)`, remove it from candidates, repeat. This gives exact without-replacement semantics.

## Implementation steps (developer-facing)

1. **Create `nl_processing/sampling/__init__.py`** — empty file.

2. **Create `nl_processing/sampling/service.py`:**

3. **Implement `WordSampler` class:**

   ```python
   class WordSampler:
       def __init__(self, *, user_id: str,
                    source_language: Language = Language.NL,
                    target_language: Language = Language.RU,
                    exercise_types: list[str],
                    positive_balance_weight: float = 0.01) -> None:
   ```

   - Validate `exercise_types` is non-empty — raise `ValueError` if empty
   - Validate `positive_balance_weight` is in `(0, 1]` — raise `ValueError` if invalid
   - Create `ExerciseProgressStore(user_id=..., source_language=..., target_language=...)`
   - Store all parameters

4. **Implement `sample(self, limit: int) -> list[WordPair]`:**
   - If `limit <= 0`, return `[]`
   - Call `self._progress_store.get_word_pairs_with_scores(self._exercise_types)` → `list[ScoredWordPair]`
   - If no candidates, return `[]`
   - For each `ScoredWordPair`, compute weight:
     - `min_score = min(scored_pair.scores[et] for et in self._exercise_types)` (missing scores = 0, already handled by ExerciseProgressStore)
     - If `min_score > 0`: weight = `self._positive_balance_weight`
     - Else: weight = `1.0`
   - If `limit >= len(candidates)`, return all candidates' pairs in random order
   - Perform weighted sampling without replacement:
     - Build candidates list and weights list
     - Iteratively: pick one via `random.choices(candidates, weights, k=1)`, remove it, adjust weights, repeat until `limit` reached
   - Return `list[WordPair]` (extract `.pair` from each `ScoredWordPair`)

5. **Implement `sample_adversarial(self, source_word: Word, limit: int) -> list[WordPair]`:**
   - Validate `source_word.language == self._source_language` — raise `ValueError` if mismatch
   - If `limit <= 0`, return `[]`
   - Call `self._progress_store.get_word_pairs_with_scores([])` → all pairs (no scores needed for adversarial)
   - Filter: `candidate.pair.source.word_type == source_word.word_type`
   - Exclude: `candidate.pair.source.normalized_form == source_word.normalized_form`
   - If fewer than `limit` candidates, return all in random order
   - Uniform random sampling without replacement: `random.sample(candidates, limit)`
   - Return `list[WordPair]`

6. **200-line awareness**: One class, two public methods, constructor. Should be well within 200 lines.

7. Run `make check`.

## Production safety constraints (mandatory)

- **Database operations**: Read-only via ExerciseProgressStore. No writes.
- **Resource isolation**: DATABASE_URL from Doppler dev environment.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses ExerciseProgressStore from database module — no reimplementation of score reading.
- **Correct file locations**: `sampling/service.py` per architecture doc.
- **No regressions**: New files only.

## Error handling + correctness rules (mandatory)

- `ValueError` for invalid constructor params (empty exercise_types, out-of-range weight).
- `ValueError` for language mismatch in `sample_adversarial`.
- Database exceptions propagate unchanged (ConfigurationError, DatabaseError).
- No silent fallbacks.

## Zero legacy tolerance rule (mandatory)

- No old code in sampling module (it was empty).

## Acceptance criteria (testable)

1. `nl_processing/sampling/__init__.py` exists (empty).
2. `nl_processing/sampling/service.py` defines `WordSampler` class.
3. Constructor validates `exercise_types` (non-empty) and `positive_balance_weight` (in (0,1]).
4. `sample(limit)` returns weighted-sampled `list[WordPair]` without replacement.
5. `sample(0)` and `sample(-1)` return `[]`.
6. `sample_adversarial(source_word, limit)` returns same-POS, different-word pairs.
7. `sample_adversarial` validates `source_word.language`.
8. All public methods are `async def`.
9. File under 200 lines.
10. `make check` passes.

## Verification / quality gates

- [ ] WordSampler implemented with correct interface
- [ ] Weight computation matches v1 spec
- [ ] Sampling is without replacement
- [ ] Adversarial sampling filters by POS and excludes source word
- [ ] Input validation for all parameters
- [ ] File under 200 lines
- [ ] `make check` passes

## Edge cases

- User has 0 words → `sample()` returns `[]`
- User has 3 words, `sample(10)` → returns all 3 in random order
- All words have positive scores → all get `positive_balance_weight`, sampling is nearly uniform among them
- All words have non-positive scores → all get weight 1.0, sampling is uniform
- `sample_adversarial` with no matching POS → returns `[]`
- `sample_adversarial` where only the source_word matches POS → returns `[]` (excluded)
- `exercise_types` with one type vs multiple — min_score behavior differs

## Notes / risks

- **Risk**: Weighted without-replacement sampling with iterative approach may be slow for very large candidate sets.
  - **Mitigation**: PRD says <200ms for 1k candidates / 50 samples. Iterative approach with list operations is O(n*k) — feasible for this scale.
- **Risk**: `random.choices` is not cryptographically secure.
  - **Mitigation**: Not needed — this is practice word selection, not security.
