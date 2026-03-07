---
Task ID: `T12`
Title: `Update vulture_whitelist.py for new/changed APIs`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T11`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update `vulture_whitelist.py` to reflect the new and changed public APIs: add entries for `ExerciseProgressStore.export_remote_snapshot`, `ExerciseProgressStore.apply_score_delta`, `AbstractBackend.check_event_applied`, `AbstractBackend.mark_event_applied`, and `ScoredWordPair.source_word_id`. Remove stale entries for deleted/renamed method parameters. Run `uv run vulture` and `make check` to confirm zero dead code false positives.

## Context (contract mapping)

- Requirements: Sprint request — all API changes finalized
- Current: `vulture_whitelist.py` (116 lines) whitelists old API surface.
- New APIs need whitelisting: `export_remote_snapshot`, `apply_score_delta`, `check_event_applied`, `mark_event_applied`, `source_word_id` field.
- Changed APIs: `exercise_type` param removed from `increment_user_exercise_score` — but vulture whitelists abstract method params by name, not by method. Check if `exercise_type` is still used elsewhere.

## Preconditions

- T11 completed (all tests pass — full sprint verified).

## Non-goals

- Modifying any source code.
- Modifying any test files.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `vulture_whitelist.py`

**FORBIDDEN — this task must NEVER touch:**
- Any source code files
- Any test files

**Test scope:**
- Verify via: `uv run vulture nl_processing tests vulture_whitelist.py`
- Full check: `make check`

## Touched surface (expected files / modules)

- `vulture_whitelist.py`

## Dependencies and sequencing notes

- Depends on T11 (all source + test changes finalized).
- This is the final task. After it passes, `make check` should be fully green.

## Implementation steps (developer-facing)

1. **Add new `ExerciseProgressStore` method entries**:
   ```python
   ExerciseProgressStore.export_remote_snapshot  # type: ignore[misc]
   ExerciseProgressStore.apply_score_delta  # type: ignore[misc]
   ```

2. **Add new `AbstractBackend` method entries**:
   ```python
   AbstractBackend.check_event_applied  # type: ignore[misc]
   AbstractBackend.mark_event_applied  # type: ignore[misc]
   ```

3. **Add new `NeonBackend` method entries**:
   ```python
   NeonBackend.check_event_applied  # type: ignore[misc]
   NeonBackend.mark_event_applied  # type: ignore[misc]
   ```

4. **Add `ScoredWordPair.source_word_id` entry**:
   ```python
   ScoredWordPair.source_word_id  # type: ignore[misc]
   ```

5. **Add new abstract method parameter names** (if new params flagged):
   - `event_id` — add to the parameter whitelist section if vulture flags it.
   - `exercise_slugs` — add to the parameter whitelist section if vulture flags it.

6. **Check for stale entries**:
   - `exercise_type` param: Still used in `increment` method of `ExerciseProgressStore`. Keep in whitelist.
   - `exercise_types` param: Now used as constructor param in `ExerciseProgressStore` and in `WordSampler`. Keep in whitelist.
   - Old `ExerciseProgressStore.get_word_pairs_with_scores` entry: method still exists (changed signature). Keep.

7. **Run vulture to verify**:
   ```
   uv run vulture nl_processing tests vulture_whitelist.py
   ```
   - Fix any new false positives by adding entries.
   - Fix any stale entries (vulture will report them as unused whitelist entries).

8. **Run full `make check`**:
   ```
   make check
   ```
   - All 8 steps must pass (ruff format, ruff check, pylint module lines, pylint bad builtins, vulture, jscpd, unit tests, integration tests, e2e tests).

9. **NOTE on `make check` and sampling**: `make check` runs `uv run pytest -n auto tests/unit` which includes `tests/unit/sampling/` tests. These tests import `ExerciseProgressStore` with the old constructor (no `exercise_types`). **This will fail.** The developer must either:
   - (a) Temporarily skip sampling tests in this sprint and document that a follow-up sprint is needed, OR
   - (b) If the sampling tests are minimal, add `exercise_types` to the sampling test fixtures as well (even though this touches `tests/unit/sampling/`).
   - **Decision**: Check if `tests/unit/sampling/` exists and if it constructs `ExerciseProgressStore`. If it does, the developer must update those constructor calls (minimal, mechanical change) even though it touches sampling test files. This is a mechanical fix, not a behavioral change. Document this deviation from the FORBIDDEN list.

10. **Line count check**: Currently 116 lines. Adding ~8 entries. Estimate ~124 lines. Under 200.

## Production safety constraints (mandatory)

- **Database operations**: `vulture_whitelist.py` is a static analysis configuration. No runtime effect.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extends existing whitelist.
- **No regressions**: Adding whitelist entries only suppresses false positives; removing stale ones is safe.

## Error handling + correctness rules (mandatory)

- N/A — static analysis configuration.

## Zero legacy tolerance rule (mandatory)

- Remove any whitelist entries that vulture reports as "unused whitelist entry" (indicates the symbol is no longer false-positive).

## Acceptance criteria (testable)

1. `uv run vulture nl_processing tests vulture_whitelist.py` — zero output (no dead code detected).
2. `make check` — all steps pass (with the caveat documented in step 9 regarding sampling tests).
3. No stale whitelist entries remaining.
4. New APIs (`export_remote_snapshot`, `apply_score_delta`, `check_event_applied`, `mark_event_applied`, `source_word_id`) are whitelisted.
5. File is ≤ 200 lines.

## Verification / quality gates

- [ ] Vulture passes with zero output
- [ ] `make check` all green
- [ ] No stale whitelist entries
- [ ] File ≤ 200 lines

## Edge cases

- Sampling tests constructing `ExerciseProgressStore` — see step 9 for handling.

## Notes / risks

- **Risk**: `make check` runs ALL unit tests (`tests/unit`), which includes sampling. If sampling tests construct `ExerciseProgressStore`, they will fail with the new constructor. The developer must handle this (see step 9). This is the only task where the FORBIDDEN boundary might need a documented exception for a mechanical fix.
- **Risk**: `npx jscpd` (duplication check) — the per-exercise-type pattern in tests may trigger duplication warnings. If so, use `// jscpd:ignore-start` / `// jscpd:ignore-end` comments on the test patterns that legitimately repeat (e.g., similar test structures for different exercise types).
