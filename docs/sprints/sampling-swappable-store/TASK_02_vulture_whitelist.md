---
Task ID: T2
Title: Add `ScoredPairProvider` to vulture whitelist and run full `make check`
Sprint: 2026-03-08_sampling-swappable-store
Module: sampling
Depends on: T1
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

After this task, `ScoredPairProvider` is whitelisted in `vulture_whitelist.py` so that vulture does not flag it as unused code. `make check` passes end-to-end, confirming the entire change set (Protocol, constructor, tests, whitelist) is clean.

## Context (contract mapping)

- Requirements: `nl_processing/sampling/docs/prd_sampling.md` — FR22 (`ScoredPairProvider` Protocol)
- Architecture: `nl_processing/sampling/docs/architecture_sampling.md` — Protocol is co-located in `sampling/service.py`
- Pattern reference: `vulture_whitelist.py` — existing whitelist entries for `database`, `sampling`, `database_cache` modules

## Preconditions

- T1 complete (`ScoredPairProvider` exists in `nl_processing/sampling/service.py`)
- `uv run pytest tests/unit/sampling/ -x -v` passes

## Non-goals

- Modifying any source code (that's T1)
- Removing existing whitelist entries
- Whitelisting anything other than `ScoredPairProvider`

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `vulture_whitelist.py` — add new entry

**FORBIDDEN — this task must NEVER touch:**
- Any module source code
- Any test files
- `nl_processing/sampling/service.py`
- `Makefile`, `pyproject.toml`, `ruff.toml`, `.jscpd.json`

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes

## Touched surface (expected files / modules)

- `vulture_whitelist.py`

## Dependencies and sequencing notes

- Depends on T1 (`ScoredPairProvider` must exist in `sampling/service.py` for the import to work)
- This is the final task — `make check` at the end validates everything

## Third-party / library research (mandatory for any external dependency)

- **Vulture**: https://github.com/jendrikseipp/vulture — dead code finder.
  - Whitelist pattern: Import the symbol so vulture considers it "used."
  - Existing project pattern in `vulture_whitelist.py`: import classes, then reference their attributes. For Protocol classes that are not instantiated, importing them is sufficient.

## Implementation steps (developer-facing)

### Step 1: Add `ScoredPairProvider` import to `vulture_whitelist.py`

Open `vulture_whitelist.py`.

1. Find the existing `sampling` imports section (near line 24):
   ```python
   from nl_processing.sampling.service import WordSampler
   ```

2. Extend it to also import `ScoredPairProvider`:
   ```python
   from nl_processing.sampling.service import ScoredPairProvider, WordSampler
   ```

3. Add an attribute reference comment in the sampling section (after the `WordSampler.sample_adversarial` line, around line 87):
   ```python
   # ScoredPairProvider — Protocol class, used structurally (never instantiated directly)
   ScoredPairProvider.get_word_pairs_with_scores  # type: ignore[misc]
   ```

4. Add `ScoredPairProvider` to the `__all__` list (maintain alphabetical order within the list):
   ```python
   "ScoredPairProvider",
   ```

### Step 2: Run vulture

```bash
uv run vulture nl_processing tests vulture_whitelist.py
```

Verify: no `ScoredPairProvider`-related output. Exit code 0.

### Step 3: Run full `make check`

```bash
make check
```

This runs:
1. `ruff format` — code formatting
2. `ruff check --fix` — linting
3. `pylint` — 200-line check + bad builtins check
4. `vulture` — dead code detection
5. `jscpd` — copy-paste detection
6. `pytest tests/unit` — all unit tests
7. `pytest tests/integration` — all integration tests (via doppler)
8. `pytest tests/e2e` — all E2E tests (via doppler)

All must pass.

### Step 4: Verify file line counts

```bash
wc -l nl_processing/sampling/service.py
```

Must be ≤ 200.

## Production safety constraints (mandatory)

- **Database operations**: N/A — whitelist file has no runtime logic.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow existing whitelist patterns exactly.
- **Correct file locations**: `vulture_whitelist.py` (existing file at repo root).
- **No regressions**: Only adding entries, not removing.

## Error handling + correctness rules (mandatory)

- N/A — whitelist file has no runtime logic.

## Zero legacy tolerance rule (mandatory)

- No legacy entries to remove — only additions.
- After this task, `make check` passes with zero warnings.

## Acceptance criteria (testable)

1. `vulture_whitelist.py` imports `ScoredPairProvider` from `nl_processing.sampling.service`.
2. `vulture_whitelist.py` references `ScoredPairProvider.get_word_pairs_with_scores`.
3. `ScoredPairProvider` is in the `__all__` list.
4. `uv run vulture nl_processing tests vulture_whitelist.py` exits with code 0.
5. `make check` passes end-to-end.

## Verification / quality gates

- [ ] `uv run vulture nl_processing tests vulture_whitelist.py` passes
- [ ] `make check` passes
- [ ] No new warnings introduced
- [ ] `nl_processing/sampling/service.py` ≤ 200 lines (re-confirmed)

## Edge cases

- If vulture flags other pre-existing issues, they are out of scope for this task. Only `ScoredPairProvider`-related flags should be addressed.

## Rollout / rollback (if relevant)

- Rollout: N/A — whitelist is a dev-only file.
- Rollback: Remove the added lines from `vulture_whitelist.py`.

## Notes / risks

- **Risk**: `make check` fails due to pre-existing issues unrelated to this sprint.
  - **Mitigation**: Run `make check` before starting the sprint to confirm baseline is green. If it fails on pre-existing issues, document them and proceed — they are not caused by this sprint.
