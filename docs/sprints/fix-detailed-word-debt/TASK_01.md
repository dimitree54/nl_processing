---
Task ID: T1
Title: Fix `DetailedWordRecord.payload` type and remove type ignores
Sprint: `2026-03-13_fix-detailed-word-debt`
Module: database, extract_word_details
Depends on: --
Parallelizable: no
---

## Goal / value

After this task, `DetailedWordRecord.payload` accepts arbitrarily nested JSON structures (as returned by POS-specific `model_dump()`), all `# type: ignore[assignment]` comments are removed from `detailed_store.py`, and `make check` passes in all three affected packages -- including `extract_word_details` integration tests that call the real OpenAI API.

## Context (contract mapping)

- BR-9 in `packages/database/docs/module-spec.md`: "Detailed-word rows must store only schema-validated payloads and must be parseable through the extractor-owned registry."
- CR-4: "`DetailedWordStore` must round-trip payloads through the same schema registry."
- The current payload type `dict[str, str | int | bool | list[str] | dict[str, str]]` cannot represent nested structures like `list[dict[str, str | None]]` (used by `common_phrases`, `example_sentences`), causing Pydantic `ValidationError` at line 153 of `service.py` and requiring 5 `# type: ignore` comments.

## Preconditions

- All three packages (`database`, `database_cache`, `extract_word_details`) are buildable (their `make check` may fail on the payload type issue, which this task fixes).

## Non-goals

- Adding `PayloadValidatorPort` or runtime validation (that is T2).
- Modifying the SQL schema or backend methods.
- Changing the serializer return type in `extract_word_details` (it already returns `dict[str, object]`, which is correct).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**

- `packages/database/src/nl_processing/database/detailed_models.py` -- change payload type
- `packages/database/src/nl_processing/database/detailed_store.py` -- remove `# type: ignore` comments, update inline type annotations
- `packages/database/tests/` -- update test payloads if needed
- `packages/database_cache/tests/` -- update test payloads if needed (unlikely, but allowed)
- `packages/extract_word_details/tests/` -- verify pass (no changes expected)

**FORBIDDEN -- this task must NEVER touch:**

- `packages/core/` -- do not modify core models
- `docs/requirements/`, `docs/architecture/`
- `packages/extract_word_details/src/` -- serializer already correct
- Root configs

**Test scope:**

- `make check` in `packages/database/`
- `make check` in `packages/database_cache/`
- `make check` in `packages/extract_word_details/`

## Touched surface (expected files / modules)

- `packages/database/src/nl_processing/database/detailed_models.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- Possibly `packages/database/tests/unit/database/test_detailed_models.py` (update type assertions)

## Dependencies and sequencing notes

- This is the foundation task. T2 and T3 both depend on it.
- Must be completed first because the type change unblocks the integration tests and the removal of type ignores.

## Third-party / library research (mandatory for any external dependency)

- **Pydantic v2**: `dict[str, JsonValue]` where `JsonValue` is a recursive type alias works correctly in Pydantic v2. Pydantic will accept any JSON-serializable nested structure without running field-level validators on individual dict values. The `model_dump()` output of any Pydantic model is always JSON-serializable and will satisfy this type.
  - Official docs: https://docs.pydantic.dev/latest/concepts/types/#json-type
  - The `JsonValue` type alias from `pydantic` exists as `pydantic.JsonValue` in Pydantic v2.9+, but defining our own is safer and avoids import coupling. A local recursive alias `JsonValue = str | int | float | bool | None | list['JsonValue'] | dict[str, 'JsonValue']` is the standard pattern.

- **Ruff `builtins.object` ban**: The ruff config bans `builtins.object` as a standalone type annotation. Using `object` as a type parameter (`dict[str, object]`) may or may not trigger this rule depending on ruff's implementation. The safer approach is the `JsonValue` recursive type alias which avoids `object` entirely.
  - Ruff TID251 docs: https://docs.astral.sh/ruff/rules/banned-api/
  - The ban is on `builtins.object` which matches `x: object` annotations. Whether `dict[str, object]` triggers it must be tested empirically in step 1 below.

## Implementation steps (developer-facing)

1. **Test if `dict[str, object]` triggers ruff ban**: In `detailed_models.py`, temporarily change the payload type to `dict[str, object]` and run `ruff check packages/database/src/nl_processing/database/detailed_models.py`. If ruff flags `TID251` for `builtins.object`, proceed with the `JsonValue` approach. If it passes, `dict[str, object]` is simpler and acceptable.

2. **Define the payload type** (based on step 1 result):
   - **If `dict[str, object]` passes ruff**: Use `payload: dict[str, object]` directly. No type alias needed.
   - **If `dict[str, object]` triggers ruff**: Define a recursive type alias at the top of `detailed_models.py`:
     ```python
     JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
     ```
     Then use `payload: dict[str, JsonValue]`.

3. **Update `detailed_models.py`**: Change the `payload` field type on `DetailedWordRecord` to the chosen type from step 2.

4. **Update `detailed_store.py`**: 
   - Remove all 5 `# type: ignore[assignment]` comments (lines 66, 69, 138, 159, 162).
   - Update the inline type annotation on `payload` variables (lines 66 and 159) to match the new type.
   - The `isinstance(payload_raw, str)` checks remain -- they handle the mock backend (JSON string) vs real backend (dict) difference. Only the declared type of the `payload` variable changes.

5. **Verify `_serializer.py` compatibility**: Read `packages/extract_word_details/src/nl_processing/extract_word_details/_serializer.py`. The `serialize_payload()` function already returns `dict[str, object]`. If the payload type is `dict[str, JsonValue]`, confirm that `dict[str, object]` is assignable to `dict[str, JsonValue]` (it is, since `object` is a supertype -- but Pydantic coercion handles the actual runtime values). No changes to serializer should be needed.

6. **Update tests if needed**:
   - Check `packages/database/tests/unit/database/test_detailed_models.py`: The test payloads like `{"article": "de", "plural": "honden"}` are `dict[str, str]` which is a valid subtype of both `dict[str, object]` and `dict[str, JsonValue]`. No changes expected.
   - Check `packages/database/tests/unit/database/test_detailed_store_get.py` and `test_detailed_store_extract.py`: Same reasoning -- simple string-value dicts will still work.
   - Check `packages/database_cache/tests/`: Same reasoning.

7. **Run `make check` in all three packages**:
   - `make check` in `packages/database/` -- must be 100% green
   - `make check` in `packages/database_cache/` -- must be 100% green
   - `make check` in `packages/extract_word_details/` -- must be 100% green, including integration tests that call the real OpenAI API (these were previously failing with `ValidationError` because the LLM-returned nested payloads couldn't fit the old type)

## Production safety constraints (mandatory)

- **Database operations**: No database schema changes. Only Python type annotations change. Integration/e2e tests target the test database via `doppler run --`.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using standard Python type annotation patterns. No new libraries.
- **Correct file locations**: Changes confined to existing files.
- **No regressions**: The type is being widened (more permissive), so all existing tests that construct `DetailedWordRecord` with simple payloads will continue to work. The only "fix" is that nested payloads (from real LLM output) are now also accepted.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: The entire point is removing `# type: ignore` comments that silence type errors.
- Removing type ignores means the code must type-check cleanly after the change.

## Zero legacy tolerance rule (mandatory)

- All 5 `# type: ignore[assignment]` comments in `detailed_store.py` must be removed.
- No dead code or workaround paths remain.

## Acceptance criteria (testable)

1. `DetailedWordRecord(payload={"key": [{"nested": "value"}]})` constructs without error.
2. `DetailedWordRecord(payload={"key": {"nested": None}})` constructs without error.
3. Zero `# type: ignore` comments exist in `detailed_store.py`.
4. `make check` passes in `packages/database/` (unit + integration + e2e).
5. `make check` passes in `packages/database_cache/` (unit + integration + e2e).
6. `make check` passes in `packages/extract_word_details/` (unit + integration + e2e, including `test_live_extraction.py` which calls real OpenAI API).
7. `ruff check` passes on `detailed_models.py` and `detailed_store.py` with zero violations.

## Verification / quality gates

- [x] Unit tests added/updated (where applicable)
- [x] Integration/e2e tests pass (verify existing tests)
- [x] Linters/formatters pass (`ruff format`, `ruff check`, `pylint` line limit, `pylint` banned builtins)
- [x] No new warnings introduced
- [x] Task ends in a working, tested state

## Edge cases

- **Empty payload `{}`**: Already tested and works -- empty dict is valid for any dict type.
- **Payload with `None` values**: `{"key": None}` must be accepted. The old type did not allow `None` values. The new type does (via `JsonValue` which includes `None`). Verify existing tests don't break.
- **Payload with numeric values**: `{"count": 42}` is valid under both old and new types.
- **Payload with deeply nested structures**: `{"phrases": [{"text": "hello", "translation": None}]}` -- this is the key case that was failing. Must work.

## Notes / risks

- **Risk**: If `dict[str, object]` is chosen and ruff silently accepts it now but a future ruff version flags it, we'd need to switch to `JsonValue`. Mitigation: The `JsonValue` approach is always safe and more explicit.
- **Risk**: Pydantic may serialize `JsonValue` type alias differently in `model_dump()` output. Mitigation: `model_dump()` doesn't care about the declared type -- it serializes the actual runtime values. The type annotation only affects validation on construction.
