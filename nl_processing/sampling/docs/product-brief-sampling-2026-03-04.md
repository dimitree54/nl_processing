---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/database/docs/product-brief-database-2026-03-02.md
  - nl_processing/database/docs/prd_database.md
  - nl_processing/database/docs/architecture_database.md
date: 2026-03-04
author: Dima
parentBrief: docs/planning-artifacts/product-brief.md
---

# Product Brief: sampling

> For shared project context (technology stack, target users, design principles), see the [shared product brief](../../../docs/planning-artifacts/product-brief.md).

## Executive Summary

`sampling` is a lightweight module that selects practice items (word translation pairs) for a specific user. It reads the user's known words from the `database` module and uses per-exercise, per-user performance scores (also stored in the database) to do weighted random sampling.

In addition to weighted practice sampling, the module provides a second helper for multiple-choice style exercises: given a word, it can sample "adversarial" distractor words from the same user's dictionary that share the same part of speech (часть речи). This adversarial sampling is uniform (no weights).

The first version intentionally uses a simple rule:

- If a word's balance for an exercise is positive (more correct than incorrect answers), it is down-weighted (default: 1/100).
- If the balance is non-positive (<= 0), it is sampled at full weight (1).

The module performs no LLM calls and has no prompt assets. Its only external dependency is the project's Neon PostgreSQL database via the `database` module.

### What Makes This Module Special

- **Adaptive practice with minimal logic:** A transparent weighting rule yields better-than-uniform practice without committing to a complex spaced repetition algorithm.
- **Per-exercise independence:** Scores are tracked independently per exercise type, so different drills can converge at different rates.
- **Database-backed, pipeline-friendly:** Uses the unified `Word` model and returns word translation pairs ready to be used in quizzes.
- **Multiple-choice ready:** Can generate part-of-speech-matched distractors for a given word without introducing new domain logic into callers.

---

## Core Vision

### Problem Statement

Once a user has a growing personal word list, uniformly random practice is inefficient: it over-samples already-mastered words and under-samples weak spots. The project needs a small, composable module that can select words for practice based on user performance signals.

### Proposed Solution

A Python module that:

- Reads a user's translated word pairs for a given language pair from `database`
- Reads per-exercise scores for those words (user-scoped, not global)
- Performs weighted random sampling of N words based on the score-derived weights
- Returns the sampled items as a list of word translation pairs
- Returns the sampled items as a list of word translation pairs
- Provides a helper to sample part-of-speech-matched distractors from the same user's dictionary (for multiple-choice options)

---

## Success Metrics

### Acceptance Criteria

1. **Correctness:** Returned pairs belong to the requested user and language pair and have valid translations.
2. **Weighting behavior:** Words with non-positive balance are sampled much more often than words with positive balance (configurable ratio).
3. **Exercise independence:** Requesting different exercise types changes the sampled distribution without affecting stored scores.
4. **Minimalism:** One class, one primary method; no prompts; no API keys beyond database configuration.

### Readiness Criteria

- Sampling works on an arbitrary-size user word list and returns unique pairs (no duplicates) up to N
- Database access errors surface as typed database exceptions (no silent fallbacks)

---

## Scope

This module has no MVP/phased delivery. The first release is intentionally small.

### Core Features

1. **Minimal public interface:** Instantiate a sampler with `user_id`, language pair, and exercise types; call one async method to sample
2. **Weighted sampling:** v1 rule based on score sign (positive vs non-positive) with configurable down-weight factor
3. **No translation logic:** Samples only from already-translated word pairs stored in the database
4. **Adversarial distractors:** Sample N additional word translation pairs with the same part of speech as a provided word (uniform sampling, no weights)

### Out of Scope

- Spaced repetition scheduling (SM-2, Leitner, time decay)
- Storing per-attempt history (timestamps, answer durations, prompt variants)
- Semantic difficulty or contextual sampling (sentences, topics)

### Future Vision

- Replace the v1 sign-based weighting with a pluggable policy (time decay, sigmoid on score, per-exercise thresholds)
- Add optional constraints (avoid recently asked items, ensure variety by part of speech)
- Support sampling across multiple language pairs
