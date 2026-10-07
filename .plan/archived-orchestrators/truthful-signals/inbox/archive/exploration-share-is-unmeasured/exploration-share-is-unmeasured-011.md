envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T07:29:39Z

component=plan-marshall:phase-6-finalize
category=improvement
title=review-retrospective runs before the loop-back and is never regenerated, so the persisted review-coverage artifact under-reports the run that actually shipped

# The final review-coverage record says "1 reviewer, 0 actionable comments" for a run that ended with 7 inline findings and 4 fix tasks

## Observation

Plan `exploration-share-is-unmeasured` / PR #1043. The persisted artifacts say:

- `review-retrospective.md`: coverage **1-of-3** at HEAD `0739dac8`; `total_findings: 1`, `reviewer_count: 1`; verdict *"1 of 3 configured reviewers ran, found nothing actionable"*.
- `status.metadata.phase_steps["6-finalize"]["project:finalize-step-review-retrospective"].display_detail`: **"1 reviewer compared (1-of-3 coverage), 0 actionable comments"**.

What actually happened afterwards:

- The pre-merge rebase produced a new HEAD, which **reset CodeRabbit's rate-limit window**.
- CodeRabbit then performed a genuine review and filed **7 inline findings**.
- Those produced **4 fix tasks (TASK-12..15)** — including a real defect where this plan's 390-line insertion **split an existing test class, stranding 6 methods under the wrong class**.
- The plan's findings store holds **13 `pr-comment` findings**, not 1.

Review coverage on the run as a whole was **2-of-3**, not 1-of-3, and the second reviewer was the one that found real defects. The persisted artifact records none of it.

## Mechanism

Three configured behaviours compose into a guaranteed miss:

1. `project:finalize-step-review-retrospective` is ordered **before** `branch-cleanup` in `phase_6.steps`, i.e. before the pre-merge rebase and before the loop-back that the rebase's review findings trigger.
2. `automatic-review` runs with `re_review_on_loopback: false`.
3. `mark-step-done` is idempotent-on-match and the step is never re-fired, so the first `display_detail` is the permanent record.

The artifact is therefore **structurally incapable** of reflecting any review that arrives after the first pass. It is not a race — it is the ordering.

## Rule

- **A retrospective-shaped step must run last, or run again.** Any step that summarises the run cannot be positioned before the loop-back that changes the run. Either move `review-retrospective` after `branch-cleanup`, or force regeneration on every loop-back re-entry.
- **A step's `display_detail` is a claim about the final state, and an idempotent write makes the first claim permanent.** For summarising steps, later executions must overwrite (`--force`) rather than no-op.
- Coverage numbers must be timestamped against a HEAD. "1-of-3 at HEAD `0739dac8`" is honest; the same sentence read as the run's coverage is not.

## What was right

The `review-retrospective.md` body is otherwise exemplary: it explicitly refuses to read CodeRabbit's `completed: true` check-run as a review, names the rate-limit refusal, and states the correct framing ("no reviewer raised an objection" is not "three reviewers inspected the diff"). The document's *reasoning* is exactly the epic's thesis. Its *scope* is the defect — it reasoned impeccably about a snapshot it never learned was superseded.

## Relation to prior message

Candidate-lesson `-004` recorded the `completed: true`-over-a-refusal signal. This is the adjacent failure: even after that refusal was correctly detected and documented, the **subsequent genuine review** never reached the persisted record. Detecting a false green is not sufficient if the artifact then freezes.

## Residue

Not fixed.
