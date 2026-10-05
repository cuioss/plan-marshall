envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T15:50:47Z

component=plan-marshall:phase-6-finalize
category=improvement

# Candidate lesson: self-review on doc-claim-heavy plans self-seeds; narrowing converges, rewording does not

- Suggested component: plan-marshall:phase-6-finalize (pre-submission-self-review, loop-back ceiling)
- Suggested category: improvement
- Signal source: Q-Gate findings and loop-back history
- Evidence: Q-Gate 6-finalize findings 559412 (ambiguous_wording, ADR README overclaim) and 922e12 (further_round_owed). Decision log fc8f11: round at 9628a85 had 2 findings plus 2 nits. Decision log c7af13: round at 03b0534 had 9 findings in 3 classes, with the note "Doc-claim half may be self-seeding". Decision log 713fc1: the operator closed the review after the last full round. Work log 20ac85: loop-back ceiling breached, iteration 4 requested against a ceiling of 3. Decision log 6cb273: the operator authorized iteration 4 past max_iterations=3.

## What happened

PLAN-13 reconciled documentation claims with code. Pre-submission self-review ran about 7 rounds. Each narrowing correction exposed the next nearby over-claim. Rounds that deleted or narrowed a claim converged. Rounds that reworded a claim produced new findings. The loop-back ceiling (max_iterations=3) was exceeded twice, both times by operator authorization.

## Why it matters

On plans that are mostly doc claims, every fix made by rewording creates new text that can be reviewed, so the review loop does not settle by itself. The loop-back ceiling then turns into a routine operator prompt instead of a backstop.

## Suggested fix

- When a self-review finding is an over-claim, prefer deleting or narrowing it to a statement that can be checked against code, rather than rewording it.
- After N rounds whose findings all come from text the plan itself wrote, report the self-seeding pattern to the operator early. Consider a separate convergence rule for doc-claim plans instead of re-running full rounds.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-13 (cuioss/cui-http #262), inbox message `plan-13-asciidoc-specs-requirements-adrs-004.md`. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
