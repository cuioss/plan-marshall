envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T23:18:36Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Order the post-run-review steps after the step that produces the evidence they review

# Order the post-run-review steps after the step that produces the evidence they review

## Context

Two finalize steps exist to look back over the whole run:

| Step | order | ran at |
|------|------:|--------|
| `project:finalize-step-review-retrospective` | 50 | 19:06:24Z |
| `default:lessons-capture` | 60 | 19:10:22Z |
| `default:branch-cleanup` | (merge gate) | 19:30:54Z → 22:47:47Z |

Everything instructive in this run happened inside `branch-cleanup`, **after**
both retrospective steps had already written their output:

- 19:43 — pre-merge review-completeness barrier BLOCKS the merge
- 19:45 / 19:47 — two monitor predicates re-armed after firing on non-events
- 19:52 — CodeRabbit posts 6 actionable comments; barrier VINDICATED
- 20:01–20:05 — triage: 4 fixes, 2 evidence-based refusals, 2 non-review
- 20:06 — loop-back to `5-execute`; TASK-011 and TASK-012
- 21:16 — post-release re-validation catches a conflict with sibling PR #1072
- 21:27 — conflict resolved and pushed

Both steps consequently shipped output that the same run then falsified.
`review-retrospective.md` declares a "thin-review landing" with "zero inline
coverage". Candidate-lesson cl9 is titled "Two of three review bots refused and
the run still merged with no durable record that the diff was unreviewed" — the
run did not merge in that state; the barrier held and the bots did review.

`plan-retrospective` sits *after* `branch-cleanup`, which is the only reason any
of this is visible. The defect is invisible from inside the steps that have it.

## Root cause

Step ordering was set by what each step *consumes at the moment it runs*, not by
when the run's evidence is *complete*. `branch-cleanup` is not merely a cleanup
step — it hosts the pre-merge barrier, the bot re-review wait, the finding
triage, the loop-back trigger and the rebase reconciliation. It is the single
largest evidence producer in the phase, and both review steps are ordered ahead
of it.

This is the same archetype as the PLAN-10 finalize-ordering defect: a step that
reviews the run cannot be ordered before the run's most informative step.

## Proposed action

1. Move `review-retrospective` and `lessons-capture` to orders after
   `branch-cleanup`, alongside `plan-retrospective` — or
2. Keep their positions but declare both `head_dependent`/re-fire-on-loop-back so
   the loop-back gate re-runs them, and require the second run to supersede the
   first artifact rather than append to it.

Option 1 is the structurally honest fix: these are post-run steps and the run is
not over at order 50. Option 2 preserves current ordering but multiplies cost —
this run's finalize already consumed 2.09M+ tokens.

3. Add a guard asserting that no step whose role is `post-run-review` is ordered
   before the merge gate.

## Evidence

- aspect: request_result_alignment — `review-retrospective.md` contradicted by
  the landed footprint (`build.py`, `test_build_verify.py`).
- aspect: plan_efficiency — `6-finalize` is the largest phase in both tokens
  (2.09M, floor) and wall-clock (5h30m); the bulk sits inside `branch-cleanup`.
- decision.log `d97f6f` (19:52:34Z) vs the review-retrospective artifact
  (19:08:23Z) — same run, opposite conclusions, 44 minutes apart.
- `work/inbox-payload-cl9.md` — a candidate-lesson whose premise the run
  subsequently refuted.
