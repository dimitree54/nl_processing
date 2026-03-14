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

## 1. Module Snapshot

### Summary

`sampling` selects practice items for a user by sampling translated word pairs with score-aware weighting. It is intentionally stateless: it reads scored pairs from a compatible provider, applies a simple weighting policy, and returns unique `WordPair` results. The module also offers an adversarial helper for multiple-choice distractors based on part-of-speech matching.

### System Context

The module sits on the hot path for practice session generation. By default it reads from `database.ExerciseProgressStore`, but its public dependency boundary is the shared `core.ports.ScoredPairProvider` protocol, so it can accept `database_cache` or any other compatible provider without API changes.

### In Scope

- Public async `WordSampler` with weighted sampling and adversarial distractor helpers.
- Score-aware sampling without replacement.
- Protocol-based scored-store injection.
- Same-part-of-speech adversarial distractor sampling.

### Out of Scope

- Owning progress state or persistence.
- Spaced repetition, decay models, or recent-item suppression.
- Semantic similarity scoring for distractors.
- Multi-language-pair orchestration beyond the configured instance.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | The simple sign-based weighting policy remains acceptable until a more advanced practice strategy is deliberately introduced. | Needs Review | Current weight rule is positive-score down-weight vs non-positive full weight. |
| A-2 | Candidate retrieval remains delegated to a scored-store dependency rather than being owned by `sampling`. | Needs Review | Keeps the module stateless. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `WordSampler(user_id, source_language, target_language, exercise_types, positive_balance_weight, scored_store?)`. | Must | Current default `positive_balance_weight` is `0.01`. |
| FR-2 | `sample(limit)` must return weighted-sampled `WordPair` results without replacement. | Must | Unique results within one sample call. |
| FR-3 | Weighting must treat non-positive score balances as full weight and positive balances as down-weighted. | Must | Current v1 rule. |
| FR-4 | Multiple `exercise_types` must aggregate by the minimum score across the configured exercises. | Must | Pessimistic aggregation. |
| FR-5 | `sample_adversarial(source_word, limit)` must return same-part-of-speech distractor pairs, exclude the source word, and sample uniformly without replacement. | Must | Multiple-choice helper. |
| FR-6 | The sampler must accept an injected scored-store that implements the shared `core.ports.ScoredPairProvider` contract. | Must | Decouples the module from one concrete backend. |

### Rules and Invariants

- BR-1: `exercise_types` must be a non-empty list.
- BR-2: `positive_balance_weight` must be in `(0, 1]`.
- BR-3: Sampling results contain no duplicates within one call.
- BR-4: Adversarial sampling requires `source_word.language` to match the sampler's configured source language.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Sampling overhead after data retrieval should stay interactive. | Target <200ms for 1k candidates / 50 samples excluding provider latency | Original module target. |
| NFR-2 | Extensibility | Data-source coupling must remain low. | Protocol-based provider injection | Supports `database` and `database_cache`. |
| NFR-3 | Simplicity | The module should stay stateless and easy to reason about. | No owned persistence | All state lives in providers. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | `limit <= 0`. | Return `[]`. | Valid no-op path. |
| FM-2 | No candidates are available from the provider. | Return `[]`. | Caller handles empty practice set. |
| FM-3 | `source_word.language` does not match the configured source language for adversarial sampling. | Raise `ValueError`. | Caller fixes input mismatch. |
| FM-4 | `positive_balance_weight` or `exercise_types` are invalid at construction time. | Raise `ValueError`. | Caller fixes configuration before sampling. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Sampling policy and adversarial distractor policy.
- Lightweight validation for sampler configuration and inputs.
- Protocol abstraction for scored-pair providers.

**Does Not Own:**

- Remote or local persistence of words and scores.
- Translation, caching, or user-progress mutation.
- Advanced scheduling or spaced-repetition algorithms.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `await sample(limit) -> list[WordPair]` | Main practice-set generator. |
| IF-2 | Python API | Inbound | Callers | `await sample_adversarial(source_word, limit) -> list[WordPair]` | Same-POS distractor helper. |
| IF-3 | Protocol | Inbound | `database`, `database_cache`, or mocks | `core.ports.ScoredPairProvider` | Core dependency abstraction. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Sampler configuration | Owned | Exercise types, weight factor, source language, and provider reference. | Runtime only | No persistent state. |
| Candidate scored pairs | Referenced | Input data retrieved from the provider. | Runtime per call | Owned by the provider. |
| Sampled `WordPair` results | Owned | Stateless output of one sampling call. | Runtime per call | Returned directly to callers. |

### Processing Flow

1. The constructor validates `exercise_types` and `positive_balance_weight`, then chooses either the injected provider or the default `ExerciseProgressStore`.
2. `sample(limit)` returns `[]` for non-positive limits, fetches scored pairs, computes weights, and performs weighted sampling without replacement.
3. `sample_adversarial(source_word, limit)` validates language, filters candidates by matching part of speech while excluding the source word, and returns a uniform random subset.
4. Callers consume the resulting `WordPair` list and keep all progress state management outside the module.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep `sampling` stateless. | Decided | The database or cache modules own score state. | Sampler behavior depends entirely on provider inputs. |
| DEC-2 | Use a simple sign-based weighting rule for v1. | Decided | Easy to explain, test, and ship. | More advanced scheduling remains deferred work. |
| DEC-3 | Aggregate multiple exercises pessimistically via minimum score. | Decided | A word is only down-weighted once it is strong across all requested exercise types. | Mixed-drill sessions remain conservative. |
| DEC-4 | Accept providers through the shared `core` protocol instead of concrete class coupling. | Decided | Enables future hot-path use of `database_cache` without API changes and keeps the protocol owned in one place. | Providers must match the structural contract. |

### Consistency Rules

- CR-1: Sampling methods must remain without-replacement within a single call.
- CR-2: New provider integrations must conform to `ScoredPairProvider` without changing the public sampler API.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, DEC-1, CR-1 | QA-1 |
| FR-4 | IF-3, DEC-3 | QA-2 |
| FR-6 | IF-3, DEC-4, CR-2 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: Weighted samples return unique `WordPair` values and respect the configured weight policy.
- AC-2: Adversarial samples return only same-part-of-speech distractors, exclude the source word, and validate source-language mismatch.
- AC-3: The sampler works both with the default remote progress store and an injected compatible provider.

### Testing Strategy

**Framework and Constraints:**

- Reuse the existing package-local unit tests and provider mocks.
- Keep the sampler itself free of live API or database dependencies whenever a mock provider is sufficient.

**Unit:**

- Constructor validation, weighting behavior, without-replacement sampling, and adversarial helper behavior.

**Integration:**

- Future integration should validate provider compatibility with real `database` or `database_cache` data if hot-path usage expands.

**Contract:**

- Verify that mock stores and `DatabaseCacheService` satisfy `ScoredPairProvider`.

**E2E or UI Workflow:**

- Sampling-driven practice-session assembly lives in consuming modules/workflows rather than here.

**Operational or Non-Functional:**

- Statistical sanity checks confirm non-positive-score items dominate sampling under the default weight factor.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Unit | Without-replacement and statistical-weighting tests | PR CI | Guards the core policy. |
| QA-2 | FR-4 | Unit | Multi-exercise aggregation tests | PR CI | Protects pessimistic min-score behavior. |
| QA-3 | FR-6 | Contract | Protocol-conformance tests for injected providers | PR CI | Keeps provider injection stable. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via package check | Preserve package quality. | PR CI | Lint or dead-code failures. |
| SC-2 | Package unit tests | Preserve weighting and adversarial behavior. | PR CI | Sampling regressions. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Practice quality of the weighting policy | Statistical checks do not prove the pedagogical usefulness of the policy. | Review sampled sessions with realistic user score distributions. | Reviewer notes or exploratory scripts. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | The v1 weighting rule may be too simplistic as user progress data grows. | Practice sessions could become less effective than intended. | Keep the strategy isolated so it can be replaced without API churn. |
| RISK-2 | The provider boundary may drift if consumers start assuming one concrete backend. | Cache or DB swaps become harder later. | Keep tests around protocol conformance and injected-store behavior. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | When should `sampling` prefer `database_cache` by default instead of building `ExerciseProgressStore` directly? | Open | Decide when cache behavior is considered stable enough for the hot path | Protocol support already makes this feasible. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending hot-path architecture decisions | Revisit if `database_cache` becomes the default provider |

### Deferred Work

- D-1: Introduce richer sampling policies only when the simple sign-based rule is proven insufficient.
- D-2: Revisit default provider selection after `database_cache` adoption decisions.

## 5. Tiered Mixed-Exercise Extension

### Change Summary

This extension adds a new tiered mixed-exercise sampling surface without changing the existing `WordSampler`, its weighting rules, or current progress-report semantics. The additive path is preferred over widening `sample()` because tiered mode must return both a word pair and the exact exercise selected for that word.

### Tiered-Mode Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| TA-1 | When a fully finished word is still sampled for review, the tiered sampler shows the most complex participating exercise. | Temporary Working Assumption | The user confirmed finished words stay eligible with down-weighting, but did not pin the review exercise explicitly. |

### Tiered Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| TFR-1 | The module must add a separate tiered sampling API such as `TieredExerciseSampler(user_id, source_language, target_language, mode_slug, exercise_types, finished_word_weight, tiered_store?)`. | Must | Keeps the existing `WordSampler` contract unchanged. |
| TFR-2 | Tiered `exercise_types` must be interpreted as ordered from lowest to highest complexity. | Must | Order is semantic in this mode. |
| TFR-3 | Tiered sampling must return records that include `WordPair`, `source_word_id`, the chosen `exercise_type`, and whether the word is currently in repeat mode. | Must | Returning only `WordPair` is insufficient for mixed exercise mode. |
| TFR-4 | A candidate word must have full sampling weight while any participating exercise score is `<= 0`. | Must | Tiered mode treats unfinished words uniformly. |
| TFR-5 | A fully finished word where all participating exercise scores are `> 0` must remain eligible, but must use a configurable `finished_word_weight` with a default of `0.01`. | Must | User-confirmed behavior. |
| TFR-6 | In normal tiered mode, the selected exercise for a sampled word must be the most complex participating exercise whose score is `<= 0`. | Must | User-confirmed behavior. |
| TFR-7 | In repeat mode, the selected exercise for a sampled word must be the most complex participating exercise whose score is `> 0`. | Must | User-confirmed behavior. |
| TFR-8 | The sampler must not mutate repeat state or scores directly; it must reflect provider-owned state and leave answer recording to persistence modules. | Must | Preserves the module's stateless ownership boundary. |
| TFR-9 | Existing `WordSampler.sample()` and `sample_adversarial()` behavior must remain unchanged when tiered mode is not used. | Must | User explicitly requested no regression in current sampling logic. |

### Tiered Rules and Invariants

- TBR-1: Tiered mode must never reorder the configured exercise list internally.
- TBR-2: Tiered sampling remains without-replacement within one call.
- TBR-3: `finished_word_weight` must be in `(0, 1]`.
- TBR-4: Missing participating scores are treated as `0`.
- TBR-5: A provider record marked as repeat mode but containing no positive participating score is invalid and must raise an explicit error instead of falling back silently.

### Tiered Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| TIF-1 | Python API | Inbound | Callers | `await sample(limit) -> list[TieredExerciseSelection]` on the new tiered sampler surface | Additive API dedicated to mixed exercise mode. |
| TIF-2 | Protocol | Inbound | `database`, `database_cache`, or mocks | Tiered candidate provider returning ordered scores plus repeat-state per word | Separate from the existing `ScoredPairProvider`. |
| TIF-3 | Change reference | Outbound | `database` | Remote tiered repeat-state persistence and mixed progress summary | See the database tiered extension section. |
| TIF-4 | Change reference | Outbound | `database_cache` | Local tiered repeat-state mirror and tiered answer-event replay | See the database_cache tiered extension section. |

### Tiered Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Tiered sampler configuration | Owned | Ordered exercises, `mode_slug`, finished-word weight, and provider reference. | Runtime only | No durable state is owned here. |
| Tiered candidate records | Referenced | Word pair, stable source ID, per-exercise scores, and repeat-state supplied by persistence. | Runtime per call | Owned by `database` or `database_cache`. |
| `TieredExerciseSelection` results | Owned | Stateless output describing which exercise to show for each sampled word. | Runtime per call | Returned directly to callers. |

### Tiered Processing Flow

1. The tiered sampler validates ordered `exercise_types`, `finished_word_weight`, and `mode_slug`, then chooses the injected provider or the default remote tiered progress store.
2. For each candidate word, the sampler assigns weight `1.0` while any participating score is `<= 0`; otherwise it uses `finished_word_weight`.
3. After selecting a word, the sampler chooses the exact exercise from the ordered list using repeat-state aware rules instead of returning only the pair.
4. Callers record the result through persistence modules, which update the exercise score as usual and mutate repeat state outside `sampling`.

### Tiered Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| TDEC-1 | Keep the existing `WordSampler` untouched and add a separate tiered sampler surface. | Decided | Protects current callers and test coverage. | Tiered callers opt into a new API. |
| TDEC-2 | Keep tiered mode stateless inside `sampling`; repeat-state persistence stays in `database` and `database_cache`. | Decided | Avoids splitting ownership of answer state. | The provider contract must supply repeat state explicitly. |
| TDEC-3 | Weight tiered candidates by "fully finished vs not fully finished" rather than by minimum score magnitude. | Decided | Matches the requested mixed-exercise semantics. | Tiered weighting intentionally differs from the classic sampler. |
| TDEC-4 | Identify one persisted tiered configuration by explicit `mode_slug` plus ordered exercises. | Decided | Prevents collisions if more than one mixed mode is introduced later. | Persistence and cache layers must validate that the stored order matches the configured mode. |

### Tiered Validation

**Acceptance Criteria:**

- TAC-1: Existing `WordSampler` unit and contract behavior remains unchanged.
- TAC-2: Tiered sampling returns unique selections that include both the word pair and the exercise chosen for that pair.
- TAC-3: Unfinished words sample with full weight, and fully finished words sample with configurable down-weighting defaulting to `0.01`.
- TAC-4: Non-repeat selections choose the most complex non-positive exercise, while repeat selections choose the most complex positive exercise.

**Testing Strategy:**

- Unit: ordered-tier selection, finished-word weighting, without-replacement sampling, and invalid repeat-state detection.
- Contract: provider mocks plus real `database` and `database_cache` tiered providers must satisfy the same candidate-provider shape.
- Regression: existing classic sampler tests remain unchanged and continue to guard the legacy path.

### Tiered Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| TRISK-1 | Returning only `WordPair` would hide the selected exercise and force caller-side reimplementation. | Different callers could diverge on which tier to show. | Keep tiered mode on a dedicated selection-returning API. |
| TRISK-2 | Tiered provider state could drift from the requested exercise order. | The sampler could choose the wrong tier for the same word. | Persist and validate an explicit `mode_slug` plus ordered exercise list. |

### Tiered Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| TOQ-1 | Should the tiered provider contract live in `sampling` first or be promoted into `core` once the shape stabilizes? | Open | Decide during implementation if a new cross-package shared contract is needed | The lower-risk path is to keep the existing `core` contract untouched initially. |
