---
Task ID: `T6`
Title: `Update vulture whitelist for new TextTranslator class`
Sprint: `2026-03-03_translate-text`
Module: `translate_text`
Depends on: `T2`
Parallelizable: `yes, with T3, T4, T5`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The `vulture_whitelist.py` is updated to replace the stale `translate_text` function reference with the new `TextTranslator` class reference (if needed), or remove the entry entirely.

## Context (contract mapping)

- Current whitelist line 9: `from nl_processing.translate_text.service import translate_text`

## Preconditions

- T2 completed: legacy `translate_text` function deleted, `TextTranslator` class exists

## Non-goals

- Updating entries for other modules

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `vulture_whitelist.py` -- update the `translate_text` entry only

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

1. **Remove** line 9: `from nl_processing.translate_text.service import translate_text`
2. **Add** (if vulture flags it): `from nl_processing.translate_text.service import TextTranslator`
3. **Update `__all__`**: Remove `"translate_text"`, add `"TextTranslator"` if needed
4. **Only change** `translate_text` entries. Leave `translate_word` and other entries untouched.
5. **Re-run vulture** to confirm: `uv run vulture nl_processing tests vulture_whitelist.py`

## Production safety constraints (mandatory)

- N/A.

## Anti-disaster constraints (mandatory)

- Only change the `translate_text` entry.

## Error handling + correctness rules (mandatory)

- N/A.

## Zero legacy tolerance rule (mandatory)

- Stale `translate_text` import removed.

## Acceptance criteria (testable)

1. `vulture_whitelist.py` no longer imports `translate_text`
2. Vulture passes without `translate_text` errors
3. Other whitelist entries unchanged
4. Ruff check passes on `vulture_whitelist.py`

## Verification / quality gates

- [ ] Vulture passes
- [ ] Ruff passes
- [ ] Other entries untouched

## Edge cases

- If `TextTranslator` is imported in tests, no whitelist entry may be needed.

## Notes / risks

- Same pattern as sprint 1's T6.
