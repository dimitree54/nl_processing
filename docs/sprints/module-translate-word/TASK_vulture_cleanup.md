---
Task ID: `T6`
Title: `Update vulture whitelist for new WordTranslator class`
Sprint: `2026-03-03_translate-word`
Module: `translate_word`
Depends on: `T2`
Parallelizable: `yes, with T3, T4, T5`
Owner: `Developer`
Status: `done`
---

## Goal / value

The `vulture_whitelist.py` is updated to replace the stale `translate_word` function reference with the new `WordTranslator` class reference (if needed), or remove the entry entirely.

## Context (contract mapping)

- Current whitelist line 10: `from nl_processing.translate_word.service import translate_word`

## Preconditions

- T2 completed: legacy `translate_word` function deleted, `WordTranslator` class exists

## Non-goals

- Updating entries for other modules

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `vulture_whitelist.py` -- update the `translate_word` entry only

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/`, test files, other whitelist entries

**Test scope:**
- Verification: `uv run vulture nl_processing tests vulture_whitelist.py`

## Touched surface (expected files / modules)

- `vulture_whitelist.py` -- modify one line

## Dependencies and sequencing notes

- Depends on T2 (legacy function must be deleted first).

## Third-party / library research (mandatory for any external dependency)

- **Tool**: `vulture` (>=2.14.0) -- dead code detection.

## Implementation steps (developer-facing)

1. **Remove** line 10: `from nl_processing.translate_word.service import translate_word`
2. **Add** (if vulture flags it): `from nl_processing.translate_word.service import WordTranslator`
3. **Update `__all__`**: Remove `"translate_word"`, add `"WordTranslator"` if needed
4. **Only change** `translate_word` entries. Leave other entries untouched.
5. **Re-run vulture**: `uv run vulture nl_processing tests vulture_whitelist.py`

## Production safety constraints (mandatory)

- N/A.

## Anti-disaster constraints (mandatory)

- Only change the `translate_word` entry.

## Error handling + correctness rules (mandatory)

- N/A.

## Zero legacy tolerance rule (mandatory)

- Stale `translate_word` import removed.

## Acceptance criteria (testable)

1. `vulture_whitelist.py` no longer imports `translate_word`
2. Vulture passes without `translate_word` errors
3. Other whitelist entries unchanged
4. Ruff check passes on `vulture_whitelist.py`

## Verification / quality gates

- [ ] Vulture passes
- [ ] Ruff passes
- [ ] Other entries untouched

## Edge cases

- If `WordTranslator` is imported in tests, no whitelist entry may be needed.

## Notes / risks

- Same pattern as the other sprints' T6 tasks.
