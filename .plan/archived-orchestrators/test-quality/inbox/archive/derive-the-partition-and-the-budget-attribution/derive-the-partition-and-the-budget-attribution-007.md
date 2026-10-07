envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T08:57:55Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=medium
source_plan=derive-the-partition-and-the-budget-attribution

# Bound self-review re-firing: 4 rounds cost 679K of the 3.57M finalize spend

## Context

Finalize is this plan's cost centre, not implementation:

| Phase | Worked | Tokens | Share |
|---|---|---|---|
| 5-execute | 1h8m | 1,437,812 | 24% |
| 6-finalize | 2h19m | 3,572,386 | 60% |

Finalize consumed 2.5x what execute did, and its spend is dominated by re-firing rather than first-pass work. Firing counts from `status.json`: `pre-push-quality-gate` 6, `pre-submission-self-review` 4 (3 failed), `project:finalize-step-plugin-doctor` 3, `ci-verify` 2, `push` 2, `automatic-review` 2, `finalize-step-simplify` 2.

The plan-efficiency anchors for `single_module + feature` are 1.0M warning / 1.6M error. Observed: 5,991,048 tokens — 3.7x the error anchor — and 243 worked minutes against a 120-minute error anchor. Every one of the four fallback ratio thresholds also trips. And because `6-finalize` never closed an `end_time`, all of these are floors.

This is not an argument that the re-firing was wrong. Round 4 of self-review examined 301 candidates and caught a genuine correctness bug. `plugin-doctor` was clean on all 3 firings; whole-tree CI was the real check and passed.

## Root cause

Two distinct contributors, worth separating because they need different remedies:

1. **Productive re-firing** — self-review rounds 1-3 each found real findings; the loop converged in 4. Decision `fae1f5` notes round 2 had "a self-seeding character" (the SKILL.md half of the flagged claim was authored by round 1's own fix), so at least part of the iteration was the loop reacting to itself.
2. **Unproductive re-firing** — `plugin-doctor` fired 3 times and was clean each time in scoped mode, with cross-skill rules structurally out of reach. `pre-push-quality-gate` fired 6 times.

## Proposed action

Measure before bounding. The cheapest concrete step is the one already proposed separately: populate the four context-load columns and run `enrich`, so the finalize phase has a `Billing (cost)` figure to reason about instead of only a dispatched-token count.

Then consider: a self-seeding guard for the self-review loop (a round whose findings target text the previous round authored is a distinct class from a round finding pre-existing drift — decision `fae1f5` already draws this line by hand); and whether a scoped `plugin-doctor` that is structurally clean should re-fire at all when the whole-tree CI check is the real gate.

## Evidence

- aspect: plan_efficiency — `max_phase_token_share 0.60`, error anchor crossed 3.7x, all 4 fallback ratios tripped
- aspect: log_analysis — 13 finalize dispatch rows; `pyproject_build` 84 calls / 4,122,990ms = 48% of all script time
- aspect: logging_gap_analysis — 3 of 13 finalize rows carry 679,275 tokens
- decision `fae1f5` — the self-seeding character of round 2, diagnosed at the time
