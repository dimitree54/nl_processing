---
Task ID: `T6`
Title: `Update vulture whitelist for new WordExtractor class`
Sprint: `2026-03-03_extract-words-from-text`
Module: `extract_words_from_text`
Depends on: `T2`
Parallelizable: `yes, with T3, T4, T5`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The `vulture_whitelist.py` is updated to replace the stale legacy `extract_words_from_text` function reference with the new `WordExtractor` class reference (if needed), or remove the entry entirely if vulture no longer flags it as unused.

## Context (contract mapping)

- Architecture: `docs/planning-artifacts/architecture.md` -- "Code Style & Quality Architecture" (vulture section)
- Current whitelist: `vulture_whitelist.py` line 8: `from nl_processing.extract_words_from_text.service import extract_words_from_text`

## Preconditions

- T2 completed: legacy `extract_words_from_text` function is deleted, `WordExtractor` class exists
- The old import in `vulture_whitelist.py` will now cause an `ImportError` during vulture analysis

## Non-goals

- Updating whitelist entries for other modules (that's their sprints)
- Changing any module source code

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `vulture_whitelist.py` -- update the `extract_words_from_text` entry

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/` -- any module source code
- `tests/` -- any test files
- Any other whitelist entries (for `translate_text`, `translate_word`, `save_translation`, `run_benchmark`)

**Test scope:**
- Verification command: `uv run vulture nl_processing tests vulture_whitelist.py`
- This should complete without errors related to `extract_words_from_text`

## Touched surface (expected files / modules)

- `vulture_whitelist.py` -- modify one line

## Dependencies and sequencing notes

- Depends on T2 (the legacy function must be deleted first).
- Can run in parallel with T3, T4, T5.

## Third-party / library research (mandatory for any external dependency)

- **Tool**: `vulture` (>=2.14.0, per `pyproject.toml`)
  - **Purpose**: Dead code detection. The whitelist file lists false-positive "unused" symbols.
  - **Usage**: `uv run vulture nl_processing tests vulture_whitelist.py`
  - **Whitelist format**: Python file with imports that vulture should not flag as unused.

## Implementation steps (developer-facing)

1. **Run vulture** to identify the current error:
   ```bash
   uv run vulture nl_processing tests vulture_whitelist.py
   ```
   This will fail because `extract_words_from_text` no longer exists as a function in `service.py`.

2. **Update `vulture_whitelist.py`**:
   - **Remove** line 8: `from nl_processing.extract_words_from_text.service import extract_words_from_text`
   - **Add** (if vulture flags `WordExtractor` as unused): `from nl_processing.extract_words_from_text.service import WordExtractor`
   - **Update `__all__`**: Remove `"extract_words_from_text"`, add `"WordExtractor"` if needed.
   - **Important**: Only change lines related to `extract_words_from_text`. Do NOT touch the `translate_text` or `translate_word` lines (those stubs still exist and will be handled by their respective sprints).

3. **Re-run vulture** to confirm no errors:
   ```bash
   uv run vulture nl_processing tests vulture_whitelist.py
   ```

4. **Note**: The `translate_text` and `translate_word` whitelist entries will still reference legacy stubs. That's correct -- those stubs still exist and those sprints will handle their cleanup.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: N/A.

## Anti-disaster constraints (mandatory)

- **No regressions**: Only change the `extract_words_from_text` entry. Leave all other entries untouched.
- **Correct file locations**: `vulture_whitelist.py` at project root.

## Error handling + correctness rules (mandatory)

- N/A for this task.

## Zero legacy tolerance rule (mandatory)

- The stale `extract_words_from_text` import is removed. This is the legacy cleanup for this module.

## Acceptance criteria (testable)

1. `vulture_whitelist.py` no longer imports `extract_words_from_text`
2. `vulture_whitelist.py` correctly references `WordExtractor` (if vulture requires it)
3. `uv run vulture nl_processing tests vulture_whitelist.py` passes without `extract_words_from_text` errors
4. Other whitelist entries (`translate_text`, `translate_word`, `save_translation`, `run_benchmark`) are unchanged
5. `uv run ruff check vulture_whitelist.py` passes

## Verification / quality gates

- [ ] Vulture passes: `uv run vulture nl_processing tests vulture_whitelist.py`
- [ ] Ruff check passes on `vulture_whitelist.py`
- [ ] Other whitelist entries untouched

## Edge cases

- If `WordExtractor` is imported and used in tests, vulture may not flag it as unused, and no whitelist entry is needed. In that case, just remove the old entry.

## Notes / risks

- **Risk**: Removing the whitelist entry might cause vulture to flag `WordExtractor` as unused if no test or caller imports it yet.
  - **Mitigation**: Check vulture output after the change. If `WordExtractor` is flagged, add it to the whitelist.
