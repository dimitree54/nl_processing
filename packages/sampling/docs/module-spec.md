---
title: "sampling Module Spec"
module_name: "sampling"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../database/docs/module-spec.md"
  - "../../database_cache/docs/module-spec.md"
---

# Module Spec: sampling

> This spec describes the module's desired target-state behavior and public contract.
> It defines WHAT the module must do, not HOW it is implemented.
> Document all public interfaces that other modules or end users are expected to use.
> Do not document implementation details such as files, internal classes, helper functions, algorithms, tests, or QA procedures unless the user explicitly requires them.
> Internal-only surfaces do not need full spec coverage, but when they could be mistaken for public API they should be marked as internal or non-contract.

## 1. Module Snapshot

### Summary

`sampling` selects a single practice item at a time from an injected scored-pair provider. The module currently exposes two public sampler classes: `WordSampler` for single-exercise weighting, and `TieredMultiExerciseSampler` for tier-aware single-item sampling over the same scored-pair input shape.

### System Context

The module sits on the hot path for practice-item selection. It owns weighting and random choice only. Candidate retrieval is delegated to an injected async provider that returns scored word pairs.

### In Scope

- `WordSampler`: single-item weighted sampling by one configured exercise type.
- `TieredMultiExerciseSampler`: single-item weighted sampling using multiple exercise scores.
- Structural provider injection through a module-local `ScoredPairProvider` protocol.

### Out of Scope

- Default backend construction or database ownership.
- Batch sampling without replacement.
- Persistence, score mutation, repeat-state mutation, or progress summaries.
- Exposing the chosen tier/exercise as part of tiered sample results.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Sampling is intentionally injection-only; callers are responsible for providing a compatible scored store. | Active | The module contract does not require a default backend. |
| A-2 | Returning a single `WordPair` per `sample()` call matches the intended hot-path usage. | Needs Review | Both public samplers currently operate one item at a time. |
| A-3 | Tiered sampling can reuse the same `ScoredWordPair` input shape instead of a separate tier-specific candidate model. | Active | No dedicated tiered provider model is part of the public contract. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `WordSampler` accepting `scored_store`, `exercise_type`, optional `positive_balance_weight` (default `0.01`), and optional `negative_balance_weight` (default `100`). | Must | Injection-only API. |
| FR-2 | `await WordSampler.sample()` must return one weighted-sampled `WordPair`. | Must | |
| FR-3 | `WordSampler` weighting must map positive scores to `positive_balance_weight`, zero scores to `1.0`, and negative scores to `negative_balance_weight`. | Must | Score is read from the configured `exercise_type`; missing scores are treated as `0`. |
| FR-4 | The module must expose `ScoredPairProvider` as the structural provider contract for both sampler classes. | Must | Requires `async get_word_pairs_with_scores() -> list[ScoredWordPair]`. |
| FR-5 | The module must expose `TieredMultiExerciseSampler` accepting `scored_store`, `exercise_types`, `tiered_exercise_type`, and optional `finished_exercise_weight` (default `0.01`). | Must | |
| FR-6 | `await TieredMultiExerciseSampler.sample()` must return one weighted-sampled `WordPair`. | Must | The chosen exercise tier is not returned. |
| FR-7 | Tiered weighting must assign `1.0` while the minimum participating score is negative, and `finished_exercise_weight` when the minimum participating score is zero or positive. | Must | Zero counts as finished for tiered weighting. |

### Rules and Invariants

- BR-1: Both samplers operate on an injected scored store and do not own persistence.
- BR-2: `WordSampler.sample()` raises an explicit error when no candidates are available.
- BR-3: `TieredMultiExerciseSampler.sample()` raises an explicit error when no candidates are available.
- BR-4: Tiered exercise ordering is significant for internal tier choice logic.
- BR-5: `TieredMultiExerciseSampler` uses the configured `tiered_exercise_type` only to determine repeat-mode behavior inside its internal helper logic.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Sampling overhead after data retrieval must stay interactive. | Single-item weighted choice should remain comfortably sub-100 ms for typical candidate sets, excluding provider latency | |
| NFR-2 | Extensibility | Data-source coupling must remain low. | Any provider satisfying `ScoredPairProvider` may be injected | Supports mocks and external stores equally. |
| NFR-3 | Simplicity | Samplers must remain stateless between calls. | No owned progress or repeat-state persistence | |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Notes |
| --- | --- | --- | --- |
| FM-1 | `WordSampler.sample()` receives an empty provider result. | Raise `RuntimeError`. | Message should make the absence of word pairs explicit. |
| FM-2 | `TieredMultiExerciseSampler.sample()` receives an empty provider result. | Raise `RuntimeError`. | Message should make the absence of word pairs explicit. |
| FM-3 | `WordSampler.sample_adversarial()` is called without the sampler having source-language context. | The behavior is non-contract. | See internal notes below. |
| FM-4 | `sample_adversarial()` receives a non-positive `limit` once source-language context exists. | Raise `ValueError`. | Carryover behavior, not part of the supported contract. |

## 3. Public Contract

### Responsibilities and Boundaries

**Responsible For:**

- Single-item weighted choice over scored word pairs.
- Interpreting one configured score for `WordSampler`.
- Interpreting multiple configured scores for `TieredMultiExerciseSampler`.
- Defining the injection contract for scored-pair providers.

**Not Responsible For:**

- Fetching, persisting, or mutating practice data.
- Constructing default providers.
- Returning tier metadata or repeat-state as part of public sample results.
- Guaranteeing `sample_adversarial()` as a supported public workflow.

### Public Interfaces

| ID | Interface Type | Direction | Counterparty | Contract Summary | Expected Behavior |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python class | Inbound | Callers | `WordSampler(scored_store, exercise_type, positive_balance_weight?, negative_balance_weight?)` | Constructs a single-exercise sampler around an injected scored store. |
| IF-2 | Python async method | Inbound | Callers | `await WordSampler.sample() -> WordPair` | Returns one weighted-sampled word pair; raises `RuntimeError` if no candidates exist. |
| IF-3 | Python protocol | Inbound | Provider implementors | `ScoredPairProvider`: `async get_word_pairs_with_scores() -> list[ScoredWordPair]` | Any object satisfying this structural protocol may be injected into either sampler. |
| IF-4 | Python class | Inbound | Callers | `TieredMultiExerciseSampler(scored_store, exercise_types, tiered_exercise_type, finished_exercise_weight?)` | Constructs a tier-aware sampler around an injected scored store. |
| IF-5 | Python async method | Inbound | Callers | `await TieredMultiExerciseSampler.sample() -> WordPair` | Returns one weighted-sampled word pair; does not expose the chosen exercise tier. |

### Internal and Non-Contract Notes

- `WordSampler.sample_adversarial()` remains in the codebase but is not part of the supported public contract for this target state.
- `TieredMultiExerciseSampler._choose_exercise_for_word()` is an internal helper. Callers must not depend on it as a supported interface.
- The tier selected by internal helper logic is not surfaced by the public `sample()` result.

### External Dependencies and Constraints

| ID | Dependency or Constraint | Why It Matters | Behavioral Assumption or Limit | Notes |
| --- | --- | --- | --- | --- |
| EC-1 | `nl_processing.core.models` (`Language`, `PartOfSpeech`, `Word`, `WordPair`, `ScoredWordPair`) | Core domain types shape all sampler inputs and outputs. | These models are stable and externally owned by `core`. | |
| EC-2 | Provider implementations such as `database` or `database_cache` | Real candidate retrieval lives outside this module. | Compatibility is structural through `ScoredPairProvider`. | No one backend is part of the contract. |

### Compatibility Notes

| ID | Area | Expectation | Impact if Broken | Notes |
| --- | --- | --- | --- | --- |
| COMP-1 | `WordSampler` constructor | Breaking: the public API is injection-only and single-exercise. | Existing callers using `user_id` or `exercise_types` no longer match the contract. | |
| COMP-2 | `WordSampler.sample()` return shape | Breaking: returns one `WordPair`, not a list. | Callers expecting batch results must adapt. | |
| COMP-3 | Tiered sampler API | Breaking: `TieredMultiExerciseSampler` returns only a `WordPair`. | Callers cannot derive the chosen exercise tier from public results. | |

## 4. Acceptance and Validation

### Acceptance Criteria

- AC-1: `WordSampler.sample()` returns a single `WordPair` selected according to configured positive, zero, and negative score weights.
- AC-2: `WordSampler.sample()` raises `RuntimeError` when the provider returns no scored pairs.
- AC-3: Any injected mock satisfying `ScoredPairProvider` can drive both samplers.
- AC-4: `TieredMultiExerciseSampler.sample()` returns a single `WordPair`.
- AC-5: Tiered weighting favors negative-score candidates over zero and positive candidates when `finished_exercise_weight` is down-weighted.
- AC-6: The internal tier-choice helper respects exercise ordering for repeat-mode and normal-mode branches.

### High-Level Validation Coverage

| ID | Target | What Must Be True | Observable Evidence or Result |
| --- | --- | --- | --- |
| VAL-1 | FR-2, FR-3 | `WordSampler` uses the configured score weights. | Under repeated sampling, negative-scored words appear more often than zero-scored words, and zero-scored words appear more often than positive-scored words. |
| VAL-2 | FR-4 | Structural provider injection works with mocks. | A simple in-memory mock provider can drive sampling successfully. |
| VAL-3 | FR-6, FR-7 | Tiered weighting follows the minimum-score rule. | Negative-score tiered candidates are sampled more often than zero or positive candidates when down-weighting is enabled. |
| VAL-4 | AC-6 | Internal tier-order logic remains stable. | Known score patterns yield the expected exercise selected by the internal helper. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | The single-item API may be too narrow for callers that still need batch selection. | Callers may reimplement batching outside the module. | Revisit only if a documented batch requirement reappears. |
| RISK-2 | Tiered sampling hides the chosen exercise tier from callers. | External consumers cannot act on the exact tier decision. | Promote tier metadata into the public return type only if a caller explicitly needs it. |
| RISK-3 | Carryover helpers that remain in code but are marked non-contract can confuse callers. | Consumers may depend on unsupported behavior. | Keep non-contract notes explicit and revisit removal or promotion deliberately. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should `sample_adversarial()` be removed, repaired, or promoted back into the supported contract? | Open | Decide explicitly before other modules depend on it. | |
| OQ-2 | Should tiered sampling return tier metadata instead of only `WordPair`? | Open | Revisit if a downstream caller needs the chosen exercise type. | |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Implicit in current module diff | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |
| RV-3 | A-3 | Implicit in current module diff | Kept as active assumption | A-3 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-4 | OQ-1 | Unresolved | Remains open pending an explicit contract decision | Revisit before supporting adversarial sampling externally. |
| RV-5 | OQ-2 | Unresolved | Remains open pending downstream requirements | Revisit if callers need tier metadata. |

### Deferred Work

- D-1: Decide whether `sample_adversarial()` should remain internal or become supported again.
- D-2: Decide whether tiered sampling should expose the chosen exercise tier publicly.
- D-3: Revisit batch sampling only if a concrete caller requirement returns.
