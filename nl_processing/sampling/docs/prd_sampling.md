---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain-skipped, step-06-innovation-skipped, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish, step-12-complete]
inputDocuments: [product-brief-sampling-2026-03-04.md]
parentPrd: docs/planning-artifacts/prd.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: low
  projectContext: greenfield
---

# Product Requirements Document - sampling

**Author:** Dima
**Date:** 2026-03-04

> For shared requirements (configuration, language support, error handling, NFRs), see the [shared PRD](../../../docs/planning-artifacts/prd.md). This document covers only module-specific requirements.

## Executive Summary

`sampling` selects a set of practice items for a user by sampling from the user's known translated word pairs stored in the `database` module. Each exercise type (e.g., "nl_to_ru", "ru_to_nl", "multiple_choice") maintains an independent per-user score per word, and `sampling` uses these scores to weight how likely each word is to be selected.

The v1 sampling policy is intentionally simple:

- For each word and exercise type, a positive score means "more correct than incorrect".
- Positive score => down-weight the word (default: 1/100).
- Score <= 0 (including missing score treated as 0) => full weight (1).

The module performs no LLM calls and makes no upstream API requests. It reads from the database only.

In addition to weighted practice sampling, the module supports "adversarial" sampling for multiple-choice exercises: given a word, sample N other words from the same user's dictionary that have the same part of speech (часть речи). This mode ignores scores and uses uniform random sampling.

## Success Criteria

### Technical Success

- Sampler returns only the requested user's word translation pairs for the specified language pair
- Weighting behavior matches the v1 policy (non-positive words dominate the sample distribution)
- Scores are treated independently per exercise type
- Sampling does not write to the database

### Measurable Outcomes

| Metric | Target | Measurement |
|---|---|---|
| Sampling correctness | 100% | Integration test assertions against DB fixtures |
| Weighting skew | Pass | Statistical sanity check (non-positive sampled more often) |
| Performance | < 200ms for 1k candidates / 50 samples (excluding DB latency) | Wall clock timing |

## Scope

No MVP/version distinction. All features described here are required for the first release.

**Post-release extensions:**
- Pluggable sampling policies (time decay, spaced repetition)
- Avoid-recently-asked constraints
- Optional stratification by part of speech

## User Journeys

### Journey 1: Build a Practice Session

**Alex, backend developer**, wants to ask a user a short quiz. He has a `user_id` and a chosen exercise type.

He instantiates a sampler for NL->RU and requests 20 items. The sampler returns `WordPair` objects (source `Word` + target `Word`). Alex renders those into questions.

### Journey 2: Mix Multiple Exercises

Alex runs a study session that includes multiple drills (e.g., "nl_to_ru" and "multiple_choice"). He requests a sample using both exercise types so that words are considered "mastered" only if they are mastered across the requested exercises.

## Developer Tool Specific Requirements

### API Surface

**Public interface:**

```python
from nl_processing.sampling.service import WordSampler
from nl_processing.core.models import Language, Word
from nl_processing.database.models import WordPair

sampler = WordSampler(
    user_id="alex",
    source_language=Language.NL,
    target_language=Language.RU,
    exercise_types=["nl_to_ru"],
    positive_balance_weight=0.01,
)

pairs: list[WordPair] = await sampler.sample(limit=20)

# Multiple choice helper: distractors with same part of speech
distractors: list[WordPair] = await sampler.sample_adversarial(
    source_word=pairs[0].source,
    limit=5,
)
```

**Exceptions:**
- Database configuration and I/O errors surface as database module exceptions (`ConfigurationError`, `DatabaseError`).

### Implementation Considerations

- `sampling` depends on `database` for: (1) user word pairs, (2) per-exercise scores.
- No LLM calls, no prompts, no `OPENAI_API_KEY` requirement.
- Exercise types are stable string identifiers stored in the database (no hard-coded list in v1).

## Functional Requirements

### Sampler Interface

- FR1: Module provides a `WordSampler` class in `sampling/service.py`
- FR2: `WordSampler` constructor accepts:
  - `user_id: str` (required)
  - `source_language: Language` (default: `Language.NL`)
  - `target_language: Language` (default: `Language.RU`)
  - `exercise_types: list[str]` (required, non-empty)
  - `positive_balance_weight: float` (default: 0.01)
- FR3: `WordSampler.sample(limit: int)` returns `list[WordPair]`
- FR4: `sample()` returns an empty list when the user has no translated word pairs for the requested language pair

### Adversarial Sampling (Multiple Choice Helper)

- FR14: `WordSampler.sample_adversarial(source_word: Word, limit: int)` returns `list[WordPair]` sampled from the same user's dictionary for the sampler's configured language pair
- FR15: `sample_adversarial()` only returns pairs whose `pair.source.word_type == source_word.word_type`
- FR16: `sample_adversarial()` excludes `source_word` itself (no identical normalized_form in the returned list)
- FR17: Adversarial sampling is uniform random sampling (no score weights)
- FR18: If `limit <= 0`, return an empty list
- FR19: If there are fewer than `limit` available distractors, return all available distractors in randomized order
- FR20: If `source_word.language` does not match the sampler's `source_language`, raise a descriptive exception

### Candidate Set

- FR5: Candidates are drawn from the user's known words in `database` and must have an available translation for the configured language pair
- FR6: Words without translations are excluded (consistent with database behavior)

### Scoring and Weighting (v1)

- FR7: For each candidate word, the sampler queries per-exercise integer scores (missing score treated as 0)
- FR8: For multiple `exercise_types`, the sampler computes `min_score = min(score[exercise_type])` across the requested exercises
- FR9: Weight function:
  - If `min_score > 0`: weight = `positive_balance_weight`
  - If `min_score <= 0`: weight = `1.0`
- FR10: `positive_balance_weight` must be in the interval `(0, 1]` (invalid values raise a descriptive exception)

### Sampling Behavior

- FR11: Sampling is weighted and is **without replacement** (no duplicate word pairs in a single result list)
- FR12: If `limit <= 0`, return an empty list
- FR13: If `limit >= number_of_candidates`, return all candidates in a randomized order

## Non-Functional Requirements (Module-Specific)

### Performance

- NFR1: Sampling computation overhead (after DB read) should be fast enough for interactive use (<200ms for 1k candidates and 50 samples on a typical dev machine)

### Extensibility

- NFR2: Sampling policy is encapsulated so it can be replaced later without changing the public interface
