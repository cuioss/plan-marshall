envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:17:46Z

component=plan-marshall:automatic-review
category=improvement
status=active

# CodeRabbit's allowance is contended fleet-wide; fire one pre-staged trigger at the stated reset

## Context

Obtaining ONE CodeRabbit review on plan `apply-the-cloud-plan-lane-contract-amendments` took **six trigger attempts over roughly five hours** (first attempt 18:53Z, review landed 23:41:13Z). Five PRs were closed unmerged in the process (#1411 through #1415); four of those (#1412-#1415) were opened purely as triggers. The review, when it finally arrived, produced 3 actionable findings — 2 Major, 1 Minor — of which 2 were fixed and 1 was deferred with recorded grounds.

The refusal ETA moved erratically across attempts: 14 min at 18:53Z, 34 min at 19:41Z, **15 seconds** at 21:24Z, 55 min at attempt 4, 57 min at 22:35Z. Read naively that looks like self-inflicted churn lengthening the penalty.

## Root cause

It is contention, not exhaustion, and not churn. PR #1410 carried two CodeRabbit review bodies the same day, so the account was actively reviewing this repository throughout. The repository had **8 open PRs sharing one per-developer allowance**, so each hourly reset was a race this plan kept losing to a sibling PR. The refusal consistently landed about 3 seconds after PR creation, and firing 5 minutes past a stated reset still lost the allowance — consistent with a sibling claiming it inside that gap, not with a penalty clock.

## Proposed action

Two changes, both cheap:

1. **Fire at the reset instant, pre-staged.** What worked on attempt 6 was pre-staging the close and the PR body so the action at the reset moment was a **single** `pr create` call. `bot_completion` then showed `in_progress=true` for the first time in six attempts — a composing review, distinguishable from the instant `completed=true` every refusal returns. Make this the documented trigger procedure rather than a technique rediscovered under pressure.
2. **Stop treating a moving ETA as evidence about our own behaviour.** Record the concurrent-open-PR count alongside the refusal, so a widening ETA is read as contention rather than as a penalty the run caused.

Consider merging into filed lesson `2026-09-03-23-002` (CodeRabbit's rate-limit ETA is unparseable and its window slides) rather than filing standalone — this extends that lesson with the contention cause and the winning technique.

## Evidence

- decision.log 2026-09-04T21:42:13Z — "Contract diagnostic run after 4 refusals: NOT account-level exhaustion. PR 1410 carries TWO coderabbitai review bodies from today ... The repo has 8 open PRs sharing one per-developer allowance, so this plan is losing the race for each reset to sibling PRs"
- decision.log 2026-09-04T22:45:55Z — "the refusal lands about 3 seconds after PR creation, and firing 5 minutes past the 22:29Z reset still lost the allowance"
- decision.log 2026-09-04T23:44:29Z — "CodeRabbit REVIEWED PR 1416 at 23:41:13Z ... obtained on attempt 6. What worked: pre-staging the close and body, then firing a SINGLE pr-create call within seconds of the stated reset"
- CodeRabbit review body #1416 — "Your plan provides up to 1 included review per hour; 0 remain after this review"
- aspect: plan_efficiency — 6-finalize consumed 2.92M of 4.45M plan tokens (66%) on a 2-file prose change
