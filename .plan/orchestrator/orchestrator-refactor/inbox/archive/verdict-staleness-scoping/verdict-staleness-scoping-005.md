envelope_version=1
sender_type=plan
sender_id=verdict-staleness-scoping
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-22T21:28:34Z

# Publish counts for every expected log category, not only top_tags[5]

## Metadata

- component: `plan-marshall:plan-retrospective`
- category: improvement
- confidence: medium
- observed_in_plan: verdict-staleness-scoping

## Context

`references/logging-gap-analysis.md` declares an expected-vs-actual table with the categories
STATUS, DECISION, ARTIFACT, VERIFY and ERROR, and asks the aspect to grade `observed /
expected_min < 0.5` as a warning. The `analyze-logs` fact extractor publishes tag counts as
`top_tags[5]` only. On this plan the top five were STATUS 112, DISPATCH 35, ARTIFACT 34,
STEP 33, OUTCOME 17 — VERIFY fell outside, so its count was never published and the row
could not be completed.

## Root cause

The producer's published surface is a ranked top-N, while the consumer's contract is a fixed
named vocabulary. A ranked list answers "what were the busiest tags", which is a different
question from "how many of each declared category were emitted". The two never agree except
by coincidence of ranking, and the shortfall is invisible: a missing row reads as an
unremarkable gap rather than as an unmeasured category.

## Proposed action

Have `analyze-logs` publish an explicit per-category count for every category named in the
logging-gap expected-pattern vocabulary — including stated zeros — alongside the existing
`top_tags[5]` ranking. Derive the vocabulary from one declared source so the producer and the
reference cannot drift.

## Evidence

- aspect: logging_gap_analysis — `expected_vs_actual` row `VERIFY,6,unmeasured`
- aspect: log_analysis — `top_tags[5]` contains STATUS, DISPATCH, ARTIFACT, STEP, OUTCOME; VERIFY is absent and bounded only at <=17
