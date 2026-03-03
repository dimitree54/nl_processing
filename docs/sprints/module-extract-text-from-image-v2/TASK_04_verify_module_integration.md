---
Task ID: `T4`
Title: `Verify service.py works with new prompt format, fix if needed, run full unit test suites`
Sprint: `2026-03-03_extract-text-v2-modifications`
Module: `extract_text_from_image`
Depends on: `T3`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Verify that the existing `service.py` works correctly with the new LangChain-native `nl.json` prompt (which now contains few-shot examples and is loaded via `langchain_core.load.load()`). Fix any issues. Run the full unit test suites for both `core/` and `extract_text_from_image/` to confirm nothing is broken. Run `make check` linting steps (ruff, pylint, vulture, jscpd) to catch any quality issues.

## Context (contract mapping)

- Architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md` — "The LangChain chain for this module differs structurally from text-only modules — it builds multi-modal messages with both text instructions and image data."
- Architecture: `docs/planning-artifacts/architecture.md` § "Quality Gate: make check"

## Preconditions

- T1 complete — no `unittest.mock` imports in test files.
- T2 complete — `core/prompts.py` uses `load()`, `nl.json` is in native format.
- T3 complete — `nl.json` has 8 messages (system + 3 few-shot pairs + placeholder).

## Non-goals

- Do not add new tests — only verify existing tests pass.
- Do not modify `benchmark.py` or `image_encoding.py`.
- Do not add new features to `service.py`.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/extract_text_from_image/service.py` — only if adjustments are needed for new prompt format
- `tests/unit/extract_text_from_image/` — only if test adjustments are needed
- `tests/unit/core/` — only if test adjustments are needed

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/core/prompts.py` (already done in T2)
- `nl_processing/extract_text_from_image/prompts/` (already done in T3)
- `pyproject.toml`, `ruff.toml`, `Makefile`

**Test scope:**
- Test commands:
  - `uv run pytest tests/unit/extract_text_from_image/ -x -v`
  - `uv run pytest tests/unit/core/ -x -v`
- Lint commands:
  - `uv run ruff format`
  - `uv run ruff check --fix`
  - `uvx pylint nl_processing tests --disable=all --enable=C0302 --max-module-lines=200`
  - `uvx pylint nl_processing tests --load-plugins=pylint.extensions.bad_builtin --disable=all --enable=W0141 --bad-functions=hasattr,getattr,setattr`
  - `uv run vulture nl_processing tests vulture_whitelist.py`
  - `npx jscpd --exitCode 1`

## Touched surface (expected files / modules)

- `nl_processing/extract_text_from_image/service.py` — likely NO changes needed, but verify
- `tests/unit/extract_text_from_image/` — likely NO changes needed, but verify
- `tests/unit/core/test_prompts.py` — likely NO changes needed (done in T2), but verify

## Dependencies and sequencing notes

- Depends on T3 because this task verifies the combined result of T1+T2+T3.
- T5 depends on this because integration tests should only be added after unit tests confirm the module works.

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries. This task only runs existing code and tests.

## Implementation steps (developer-facing)

### Step 1: Verify service.py constructor still works

```bash
uv run python -c "
import os
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-constructor-only')
from nl_processing.extract_text_from_image.service import ImageTextExtractor
extractor = ImageTextExtractor()
print('Constructor OK')
print('Chain type:', type(extractor._chain).__name__)
"
```

**Note**: The `os.environ.setdefault` here is ONLY for this one-off verification command (not in test code — tests use `monkeypatch.setenv`). We need a key set to construct `ChatOpenAI`. The chain won't be invoked.

**What to check**: The constructor should:
1. Load the new `nl.json` (8 messages) via `load_prompt()`
2. Create a `ChatOpenAI` instance
3. Compose the chain with `prompt | llm`

**Potential issue**: The old prompt had 2 messages (system + placeholder). The new prompt has 8 messages (system + 6 few-shot + placeholder). The chain composition (`prompt | llm`) should work identically because the prompt still has `input_variables == ["images"]` and the chain input is `{"images": [HumanMessage(...)]}`. The few-shot messages are static — they don't add input variables.

### Step 2: Run unit tests

```bash
uv run pytest tests/unit/extract_text_from_image/ -x -v
uv run pytest tests/unit/core/ -x -v
```

**All tests must pass.** If any fail:
- Read the failure message carefully.
- Determine if it's a prompt format issue (T2/T3 side effect) or a test mock issue (T1 side effect).
- Fix the test or the code — but prefer fixing the test if the code behavior is correct.

### Step 3: Run ruff

```bash
uv run ruff format
uv run ruff check --fix
```

Fix any errors. Common issues to watch for:
- Import ordering after adding `dumpd`/`load` imports
- Line length (120 char limit)
- Unused imports (if any were left from T1/T2)

### Step 4: Run pylint

```bash
uvx pylint nl_processing tests --disable=all --enable=C0302 --max-module-lines=200
uvx pylint nl_processing tests --load-plugins=pylint.extensions.bad_builtin --disable=all --enable=W0141 --bad-functions=hasattr,getattr,setattr
```

**Watch for**:
- File over 200 lines (unlikely — all touched files are well under)
- `hasattr`/`getattr`/`setattr` usage (old `prompt_author.py` had `hasattr` — removed in T2)

### Step 5: Run vulture

```bash
uv run vulture nl_processing tests vulture_whitelist.py
```

**Watch for**:
- New unused code introduced by T1/T2/T3
- The `generate_nl_prompt.py` script functions may be flagged as "unused" because the script is not imported anywhere. If so, add them to `vulture_whitelist.py`. **Wait** — we are NOT allowed to modify `vulture_whitelist.py` (it's outside sprint scope). The `generate_nl_prompt.py` file should be structured so the main function is called in `if __name__ == "__main__"` — vulture typically doesn't flag functions called within the same file. If vulture flags it, note it as a known issue.

### Step 6: Run jscpd

```bash
npx jscpd --exitCode 1
```

**Watch for**: Code duplication between the two test files' `_AsyncChainMock` classes (from T1). If flagged, extract to `conftest.py`.

### Step 7: Address any issues

If any step above fails:
- Fix the issue in the allowed files.
- Re-run the failing check.
- Document what was changed and why.

### Step 8: Final combined check

```bash
uv run ruff format && uv run ruff check --fix && uv run pytest tests/unit/core/ tests/unit/extract_text_from_image/ -x -v
```

## Production safety constraints (mandatory)

- No production code is modified (unless service.py needs adjustment).
- No database operations.
- No network calls (unit tests only — LLM is mocked).

## Anti-disaster constraints (mandatory)

- **Reuse before build**: No new code — only verification and minor fixes.
- **No regressions**: This task's entire purpose is regression detection.

## Error handling + correctness rules (mandatory)

- Do not suppress any test failures or lint warnings. Fix them.
- If vulture flags false positives in new files, document them but do not add `# noqa` — that requires explicit approval.

## Zero legacy tolerance rule (mandatory)

- If any dead code is found (e.g., old format references in comments, unused imports), remove it.

## Acceptance criteria (testable)

1. `uv run pytest tests/unit/extract_text_from_image/ -x -v` — all tests pass
2. `uv run pytest tests/unit/core/ -x -v` — all tests pass
3. `uv run ruff check nl_processing/ tests/` — zero errors
4. `uvx pylint nl_processing tests --disable=all --enable=C0302 --max-module-lines=200` — passes
5. `uvx pylint nl_processing tests --load-plugins=pylint.extensions.bad_builtin --disable=all --enable=W0141 --bad-functions=hasattr,getattr,setattr` — passes
6. `uv run vulture nl_processing tests vulture_whitelist.py` — passes (or known false positives documented)
7. `npx jscpd --exitCode 1` — passes
8. `ImageTextExtractor()` constructor works with the new `nl.json`

## Verification / quality gates

- [ ] Unit tests pass (core + extract_text_from_image)
- [ ] `ruff format` + `ruff check` — clean
- [ ] pylint — clean (both checks)
- [ ] vulture — clean
- [ ] jscpd — clean
- [ ] No new warnings

## Edge cases

- The new prompt has 8 messages. Some tests may assert on prompt message count or structure — update if needed.
- The `test_constructor_defaults` test constructs a real `ImageTextExtractor` with a monkeypatched API key. This will load the real `nl.json`. If the format is correct, it will work. If not, it will fail here and we'll know T2/T3 have an issue.

## Notes / risks

- **Risk**: `jscpd` flags duplication between `_AsyncChainMock` in both test files.
  - **Mitigation**: If flagged, extract `_AsyncChainMock` and `_AsyncChainMockError` into `tests/unit/extract_text_from_image/conftest.py` and import from there. This is a simple refactor.
- **Risk**: `vulture` flags functions in `generate_nl_prompt.py` as unused.
  - **Mitigation**: The functions are called within the same file's `if __name__` block. Vulture usually handles this correctly. If not, the script can use a `__all__` list or the functions can be called directly without being defined separately. Document if it's a false positive.
